from .variants import populate_variant_tables, version_table, lab_table
import bitstruct
import math
import base64
import qrcode

# One bit per Allele
VAR_NOT_FOUND = 0x0
VAR_FOUND = 0x1

# One bit for coverage
VAR_NOT_COVERED = 0x0
VAR_COVERED = 0x1

# 4 bits in total
BITS_PER_ENTRY = 4
BITS_PER_BYTE = 8

entry_cf = bitstruct.compile(
    'u1u1u1u1',
    ['allele_A', 'allele_B', 'allele_X', 'covered']
)

# Header with 3 byte token, 8 bit version id and 8 bit lab id
header_cf = bitstruct.compile(
    't24u8u8',
    ['token', 'version', 'lab']
)
HEADER_BITS = 40
HEADER_BYTES = 5

TOKEN = "p1l"

variant_tables = populate_variant_tables()


def encode_variants(variants, version, lab):
    return base64.urlsafe_b64encode(pack_variants(variants, version, lab))


def decode_variants(data):
    return unpack_variants(base64.urlsafe_b64decode(data))


def pack_variants(variants, version, lab):

    # Map the version string to the numeric version id
    internal_version = list(version_table.values()).index(version)

    # Get the variant table based on the (internal) version
    variant_table = variant_tables[internal_version]

    # Map the lab string to the numeric lab id
    internal_lab = list(lab_table.values()).index(lab)

    # Create a bytearray with the length of the token + rounded up length of compressed variants
    data = bytearray(HEADER_BYTES + math.ceil(len(variant_table) * BITS_PER_ENTRY / BITS_PER_BYTE))

    # Fill in the header
    header_cf.pack_into(data, 0, {'token': TOKEN, 'version': internal_version, 'lab': internal_lab})

    for index in variant_table:
        ref_entry = variant_table[index]

        entry = {
            'allele_A': VAR_NOT_FOUND,
            'allele_B': VAR_NOT_FOUND,
            'allele_X': VAR_NOT_FOUND,
            'covered': VAR_COVERED,
        }

        if ref_entry['gene'] in variants:
            if ref_entry['variant'] in variants[ref_entry['gene']]:
                if 'var_A' in variants[ref_entry['gene']][ref_entry['variant']]:
                    entry['allele_A'] = VAR_FOUND
                if 'var_B' in variants[ref_entry['gene']][ref_entry['variant']]:
                    entry['allele_B'] = VAR_FOUND
                if 'var_X' in variants[ref_entry['gene']][ref_entry['variant']]:
                    entry['allele_X'] = VAR_FOUND
                if 'not_covered_var' in variants[ref_entry['gene']][ref_entry['variant']]:
                    entry['covered'] = VAR_NOT_COVERED

        entry_cf.pack_into(data, HEADER_BITS + index * BITS_PER_ENTRY, entry)

    return data


def unpack_variants(data):

    # Get header from start of data
    header = header_cf.unpack_from(data)

    # Convenience variables
    token = header['token']
    version = header['version']
    lab = header['lab']

    # TODO: turn into exceptions
    assert token == TOKEN, print("Checksum failed: %s != %s" % (token, TOKEN))
    if version not in variant_tables.keys():
        raise Exception(f"Unknown version: {version}")

    # Find the variant table for this version
    variant_table = variant_tables[version]

    results = {}
    for index in variant_table:
        entry = entry_cf.unpack_from(data, HEADER_BITS + index * BITS_PER_ENTRY)
        results[index] = entry

    return results, version, lab


def create_qr(encoded_variants, url_prefix):
    url = url_prefix + encoded_variants.decode()

    qr = qrcode.QRCode(
        version=10,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=4,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=False)

    img = qr.make_image(fill_color="black", back_color="white")

    return url, img
