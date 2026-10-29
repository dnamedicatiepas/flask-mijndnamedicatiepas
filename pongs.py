"""The PONGS procedure, ported from pongs-flask (pongs/v1.py and pongs/v2.py).

A pas carries a QR code with the patient's pharmacogenetic profile encoded in
the URL. get_pas() turns that profile into the data the Mijn Pas pages show:

1. decode the profile with pongs-translation: variants for v1, alleles for v2;
2. determine the diplotype per gene (v1: haplotyping with the locus definitions;
   v2: the alleles are indexes into the translation table);
3. translate each diplotype to a G-Standaard thesaurus item number (tsitnr) with
   the translation tables from the koppelingen repository;
4. evaluate the G-Standaard pharmacogenetics protocols for those tsitnrs.

It reads the G-Standaard database (SQLALCHEMY_DATABASE_URI) and the
TRANSLATION_TABLES_DIR and LOCUS_DEFINITIONS directories from the app config.
"""
import glob
import os

import locus_processing
from flask import current_app
from flask_sqlalchemy import SQLAlchemy
from gstandaard.traversal import trav_prot, get_protocols, tsitnr2mfbpanrs, tsitnr2phenotype
from gstandaard.utils import poms2med
from translation.code import read_translation_table, alleles2tsitnr
from translation.encoding import decode_variants, decode_alleles
from translation.haplotyping import vl2json, hap, vl2cov, vl2uncov
from translation.variants import populate_variant_tables, version_table, lab_table

db = SQLAlchemy()

# The profile encodings, as in the pongs-flask URLs /v1/<profile> and /v2/<profile>.
SCHEMES = ("v1", "v2")


class InvalidProfile(Exception):
    """The encoded profile can't be decoded, or its version has no data."""


def get_pas(scheme, encoded_profile):
    """Run the procedure for one pas.

    Returns a dict with:
      lab       The lab that issued the pas (a lab_table value, e.g. "LUMC").
      version   The translation table version, e.g. "v3.0.0".
      genes     [{gene, diplotype, phenotype}] for the genes with advice.
      variants  [{gene, allele_a, allele_b, unphased, covered, not_covered}];
                v1 only, empty for v2 (an allele profile carries no variants).
      report    [{protocol, pad, action, gene, phenotype}] per advice, sorted
                by protocol (the medicine). gene/phenotype are the gene result
                that triggered the advice.

    Raises InvalidProfile if the profile can't be decoded.
    """
    if scheme == "v1":
        return _get_pas_v1(encoded_profile)
    if scheme == "v2":
        return _get_pas_v2(encoded_profile)
    raise InvalidProfile(f"Unknown scheme: {scheme}")


def _get_pas_v1(encoded_profile):
    variant_tables = populate_variant_tables()

    try:
        sample_variants, version_id, lab_id = decode_variants(encoded_profile)
        lab_string = lab_table[lab_id]
        version_string = version_table[version_id]
        variant_table = variant_tables[version_id]
    except Exception as e:
        # Anything can go wrong decoding a corrupt or made-up profile.
        raise InvalidProfile(f"Can't decode v1 profile: {e}") from e

    locus_definition_path = os.path.join(current_app.config['LOCUS_DEFINITIONS'], version_string)
    locus_files = glob.glob(locus_definition_path + '/*.yaml')
    if not locus_files:
        raise InvalidProfile(f"No locus definitions for {version_string}")

    variant_json = vl2json(sample_variants, variant_table)
    coverage = vl2cov(sample_variants, variant_table)
    non_coverage = vl2uncov(sample_variants, variant_table)

    alt_mapping = {}
    for locus_file in locus_files:
        locus = locus_processing.load_locus_yaml(locus_file)
        alt_mapping[locus.name] = {s.g_notation: s.alt_notation for s in locus.snps}

    haps = hap(variant_json, coverage, locus_definition_path)
    diplotypes = [(h['gene'], h['hap_A'], h['hap_B']) for h in haps]
    genes, tsitnrs = _translate(version_string, diplotypes)

    genes_with_advice = {g['gene'] for g in genes}

    def alt_notations(gene, g_notations):
        return ', '.join(alt_mapping[gene][g] for g in g_notations)

    variants = []
    for gene in sorted(variant_json.keys()):
        if gene not in genes_with_advice:
            continue
        variants.append({
            'gene': gene,
            'allele_a': alt_notations(gene, [v['g_notation'] for v in variant_json[gene]['a_dict']['variants']]),
            'allele_b': alt_notations(gene, [v['g_notation'] for v in variant_json[gene]['b_dict']['variants']]),
            'unphased': alt_notations(gene, [v['g_notation'] for v in variant_json[gene]['x_dict']['variants']]),
            'covered': alt_notations(gene, coverage.get(gene, [])),
            'not_covered': alt_notations(gene, non_coverage.get(gene, [])),
        })

    return {
        'lab': lab_string,
        'version': version_string,
        'genes': genes,
        'variants': variants,
        'report': _evaluate_protocols(tsitnrs),
    }


def _get_pas_v2(encoded_profile):
    tables_dir = current_app.config['TRANSLATION_TABLES_DIR']

    try:
        sample_alleles, version_id, lab_id = decode_alleles(encoded_profile, tables_dir)
        lab_string = lab_table[lab_id]
        version_string = version_table[version_id]
        translation_table = _read_translation_table(version_string)
        haps = [translation_table[idx] for idx in sample_alleles]
    except Exception as e:
        # Anything can go wrong decoding a corrupt or made-up profile.
        raise InvalidProfile(f"Can't decode v2 profile: {e}") from e

    diplotypes = [(h['gene'], h['allele_a'], h['allele_b']) for h in haps]
    genes, tsitnrs = _translate(version_string, diplotypes)

    return {
        'lab': lab_string,
        'version': version_string,
        'genes': genes,
        'variants': [],
        'report': _evaluate_protocols(tsitnrs),
    }


def _read_translation_table(version_string):
    return read_translation_table(
        os.path.join(current_app.config['TRANSLATION_TABLES_DIR'], version_string + ".yaml"))


def _translate(version_string, diplotypes):
    """Translate (gene, allele_a, allele_b) diplotypes to tsitnrs.

    Returns the gene table and {tsitnr: gene row}. A gene whose tsitnr has no
    phenotype in the G-Standaard (advice no longer available) is left out of
    the gene table, but its tsitnr is still evaluated, as in pongs-flask.
    """
    translation_table = _read_translation_table(version_string)

    genes = []
    tsitnrs = {}
    for gene, allele_a, allele_b in sorted(diplotypes):
        tsitnr = alleles2tsitnr(translation_table, gene, allele_a, allele_b)
        if tsitnr <= 0:
            continue

        # The G-Standaard pads the phenotype name with spaces.
        phenotype = tsitnr2phenotype(db.session, tsitnr)
        row = {
            'gene': gene,
            'diplotype': f"{allele_a}/{allele_b}",
            'phenotype': phenotype.strip() if phenotype else None,
        }
        tsitnrs[tsitnr] = row
        if row['phenotype']:
            genes.append(row)

    return genes, tsitnrs


def _evaluate_protocols(tsitnrs):
    """Evaluate the G-Standaard pharmacogenetics protocols for {tsitnr: gene row}."""
    protocols = get_protocols(db.session, fg_only=True)

    report = []
    for tsitnr, gene_row in tsitnrs.items():
        sample_params = tsitnr2mfbpanrs(db.session, tsitnr)

        for protocol in protocols:
            # Alleen voor testapotheken
            if protocol.mfbpwin == 'J':
                continue

            doorlopen_pad = []
            action = trav_prot(protocol.flow, sample_params, doorlopen_pad, debug=False)

            if action:
                assert len(doorlopen_pad) == 1
                report.append({
                    'protocol': poms2med(protocol.mfbpoms),
                    'pad': doorlopen_pad[0],
                    'action': action,
                    'gene': gene_row['gene'],
                    'phenotype': gene_row['phenotype'],
                })

    return sorted(report, key=lambda k: k['protocol'])
