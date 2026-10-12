import os
import glob
import yaml
import argparse
import locus_processing
import re

# TODO: move table to config file
version_table = {
    0: 'v1.0.0',
    1: 'v2.0.0',
    2: 'v3.0.0',
}

# TODO: move table to config file
lab_table = {
    0: 'LUMC',
    1: 'AmsterdamUMC',
}


def populate_variant_tables():
    file_prefix = 'variants_'
    file_suffix = '.yaml'
    relative_data_dir = 'data'

    # Determine the directory of the current module
    this_dir, _ = os.path.split(__file__)
    # Derive relative directory
    data_dir = os.path.join(this_dir, relative_data_dir)
    variant_table_filenames = glob.glob(f"{data_dir}/{file_prefix}*{file_suffix}")

    # Create a structure with a table for every version found in the directory
    variant_tables = {}
    for filename in variant_table_filenames:
        # Filename are in the shape of 'variants_vX.Y.Z.yaml'
        match = re.search(f"{file_prefix}(\S+){file_suffix}", filename)
        version = match.group(1)

        if version not in version_table.values():
            raise Exception("Unknown version: %s" % version)
        internal_version = list(version_table.values()).index(version)
        variant_tables[internal_version] = yaml.load(open(filename, "r"), Loader=yaml.SafeLoader)

    return variant_tables


def create_variants_yaml(locus_directory, variant_yaml_filename, pattern):
    locus_files = glob.glob(f"{locus_directory}/{pattern}")
    print("\nLocus files found:")
    for lf in locus_files:
        print(lf)

    variant_list = {}
    index = 0
    for locus_file in locus_files:
        locus = locus_processing.load_locus_yaml(locus_file)
        print("\nProcessing:", locus)
        locus_variants = [s.g_notation for s in locus.snps]
        for variant in locus_variants:
            variant_list[index] = {'gene': locus.name, 'variant': variant}
            index += 1
        print("Found {num_var} variants in locus.".format(num_var=len(locus_variants)))

    print(f"\nWriting {index} variants to {variant_yaml_filename}")
    with open(variant_yaml_filename, "w") as yaml_file:
        yaml.dump(variant_list, yaml_file, Dumper=yaml.SafeDumper)


# Entry point for console_script entry in setup.py
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-l", "--locus-directory", required=True,
                    help="Directory with input locus files")
    ap.add_argument("-y", "--variants-yaml", required=True,
                    help="Filename of output variant yaml")
    ap.add_argument("-p", "--pattern", required=False, default="*.yaml",
                    help="Pattern of filenames to match")
    args = vars(ap.parse_args())

    create_variants_yaml(args['locus_directory'], args['variants_yaml'], args['pattern'])


# Entry point of we are called as standalone script
if __name__ == "__main__":
    main()
