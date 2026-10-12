import xlrd
import argparse
import yaml


def alleles2tsitnr(translation_table, gene, allele_a, allele_b):
    for e in translation_table or []:
        if (gene.lower() == e['gene'].lower()) and (
            ((allele_a.lower() == e['allele_a'].lower()) and (allele_b.lower() == e['allele_b'].lower()))
            or
            ((allele_a.lower() == e['allele_b'].lower()) and (allele_b.lower() == e['allele_a'].lower()))
        ):
            return e['tsitnr'] or 0
    return 0


# Genotype to phenotype new data

COL_GENE = 0
COL_ALLELE_A = 1
COL_ALLELE_B = 2
COL_TSITNR = 3  # G-Standaard Thesaurus itemnummer


def sheet2dict(sheet):
    results = list()

    for rx in range(0, sheet.nrows):
        row = sheet.row(rx)

        if row[COL_GENE].value and row[COL_GENE].ctype == 1:
            gene = row[COL_GENE].value
        else:
            # Assuming gene read on previous line
            pass

        if row[COL_ALLELE_A].value and row[COL_ALLELE_A].ctype == 1:
            allele_a = row[COL_ALLELE_A].value
        else:
            allele_a = None

        if row[COL_ALLELE_B].value and row[COL_ALLELE_B].ctype == 1:
            allele_b = row[COL_ALLELE_B].value
        else:
            allele_b = None

        if row[COL_TSITNR].value and row[COL_TSITNR].ctype == 2:
            tsitnr = int(row[COL_TSITNR].value)
        else:
            tsitnr = None

        result = {'gene': gene, 'allele_a': allele_a, 'allele_b': allele_b, 'tsitnr': tsitnr}
        results.append(result)

    return results


def wb2dict(excel_file):
    wb = xlrd.open_workbook(excel_file)
    print("The number of worksheets is {0}".format(wb.nsheets))
    print("Worksheet name(s): {0}".format(wb.sheet_names()))
    sheet = wb.sheet_by_index(0)
    result = sheet2dict(sheet)
    return result


def read_translation_table(translation_yaml):
    with open(translation_yaml, "r") as yaml_file:
        translation_table = yaml.load(yaml_file, Loader=yaml.SafeLoader)

    return translation_table


def create_translation_table(excel_file, translation_yaml):
    translation_table = wb2dict(excel_file)
    with open(translation_yaml, "w") as yaml_file:
        yaml.dump(translation_table, yaml_file, Dumper=yaml.SafeDumper, sort_keys=False, default_flow_style=False)


# Entry point for console_script entry in setup.py
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-x", "--excel-file", required=True,
                    help="Excel file with translation table")
    ap.add_argument("-y", "--translation-yaml", required=True,
                    help="Filename of output translation yaml")
    args = vars(ap.parse_args())

    create_translation_table(args['excel_file'], args['translation_yaml'])


# Entry point of we are called as standalone script
if __name__ == "__main__":
    main()
