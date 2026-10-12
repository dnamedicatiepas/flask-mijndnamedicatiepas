import os
import csv
import argparse
import translation
import yaml


def wes2pivot(wes_csv):
    results = {}

    cols = ["var_A", "var_B", "var_X", "not_covered_var"]

    with open(wes_csv) as f:
        f_csv = csv.DictReader(f, delimiter='\t')
        for row in f_csv:

            # Create an entry for this id if not yet present
            if row['ind_id'] not in results:
                results[row['ind_id']] = {}

            # Skip genes that don't have any of the columns filled
            if not any(row[col] and row[col] != 'NA' for col in cols):
                continue

            # Create an entry for this gene if not yet present
            if row['gene'] not in results[row['ind_id']]:
                results[row['ind_id']][row['gene']] = {}

            # Try all of the columns fields
            for col in cols:
                # Skip this column if there is no value
                if not row[col] or row[col] == 'NA':
                    continue

                # split out the variants like: "('var_B', '42526694G>A;42524947C>T')" into:
                # '42526694G>A': ['var_B'] and '42524947C>T': ['var_B'
                for variant in row[col].split(';'):

                    # Create an entry for this variant if not yet present
                    if variant not in results[row['ind_id']][row['gene']]:
                        results[row['ind_id']][row['gene']][variant] = []

                    # Append the column name to the entry of this variant name
                    results[row['ind_id']][row['gene']][variant].append(col)

    return results


# Library entry point
def create_qrcodes_from_wes(wes_file, version, lab, qrcode_directory, url_prefix, config_file):
    pivot = wes2pivot(wes_file)
    import pprint

    if config_file:
        with open(config_file, 'r') as stream:
            try:
                ped = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)

        pretty_names = {}

        for sample in ped['samples']:
            name = sample['name']

            # Already magpie format
            if '_' in name:
                continue

            if sample['mother'] and sample['father']:
                mother = sample['mother']
                father = sample['father']
                pretty_names[name] = f"Child_{name}"
                pretty_names[mother] = f"Mother_{mother}"
                pretty_names[father] = f"Father_{father}"

        pprint.pprint(pretty_names)
    else:
        pretty_names = {}


    for sample_id in pivot:

        if sample_id in pretty_names:
            pretty_name = pretty_names[sample_id]
        else:
            pretty_name = sample_id

        print(f"Sample ID: {pretty_name}")

        pprint.pprint(pivot[sample_id])
        enc = translation.encoding.encode_variants(pivot[sample_id], version, lab)
        url, img = translation.encoding.create_qr(enc, url_prefix)
        print(f"URL: {url}")
        filename = f"qrcode_{pretty_name}.png"
        path = os.path.join(qrcode_directory, filename)
        print(f"Output path: {path}")
        img.save(path)

        print()


# Entry point for console_script entry in setup.py
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-w", "--wes-file", required=True,
                    help="Path to WES file that came out of pipeline")
    ap.add_argument("-v", "--version", required=True,
                    help="Version of variant table")
    ap.add_argument("-l", "--lab", required=True,
                    help="Name of the lab")
    ap.add_argument("-u", "--url-prefix", required=True,
                    help="URL to prefix results")
    ap.add_argument("-q", "--qrcode-directory", required=True,
                    help="Directory to output QR files")
    ap.add_argument("-c", "--config-file", required=False,
                    help="Config file for role mapping")
    args = vars(ap.parse_args())

    create_qrcodes_from_wes(args['wes_file'], args['version'], args['lab'], args['qrcode_directory'], args['url_prefix'], args['config_file'])


# Entry point of we are called as standalone script
if __name__ == '__main__':
    main()
