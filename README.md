# flask-mijndnamedicatiepas

The mijndnamedicatiepas.nl website and the Mijn Pas pages a patient sees after scanning the QR
code on their DNA medication pass.

The Mijn Pas pages run the PONGS procedure from
[pongs-flask](https://git.lumc.nl/pongs/pongs-flask) in this application (`pongs.py`): decode the
profile in the URL, determine the diplotype per gene, translate it to a G-Standaard thesaurus item
number (`tsitnr`) and evaluate the G-Standaard pharmacogenetics protocols. It uses the same
packages and data repositories as pongs-flask.

## Workspace layout

```
LUMC-mijndnamedicatiepas/              <- workspace (any name)
├── flask-mijndnamedicatiepas/         <- this repository
│   ├── gstandaard/                    <- gstandaard-python (pip install -e)
│   ├── pongs-translation/             <- pongs-translation, branch haplotype (pip install -e)
│   └── instance/gstandaard.db         <- G-Standaard SQLite database, built with populate-db
├── koppelingen/                       <- translation tables (diplotype -> tsitnr)
├── locus_definitions/                 <- locus definitions per gene (WES/v1.0.0 ...)
├── gstandaard_html_beschrijvingen/    <- Z-Index file descriptions, one directory per date
└── BST686T~/                          <- a G-Standaard delivery from Z-Index (BST<nr>T files)
```

`gstandaard/`, `pongs-translation/` and `instance/` are not tracked by this repository. The
G-Standaard is licensed data from [Z-Index](https://www.z-index.nl): never commit it.

## Setup

From the workspace directory:

```sh
git clone https://github.com/dnamedicatiepas/flask-mijndnamedicatiepas.git
git clone https://github.com/dnamedicatiepas/gstandaard-python.git flask-mijndnamedicatiepas/gstandaard
git clone -b haplotype https://git.lumc.nl/pongs/pongs-translation.git flask-mijndnamedicatiepas/pongs-translation

git clone https://git.lumc.nl/pongs/koppelingen.git
git clone https://git.lumc.nl/pongs/locus_definitions.git
git clone https://git.lumc.nl/pongs/gstandaard_html_beschrijvingen.git
```

Place the G-Standaard delivery from Z-Index in the workspace as well, for example as `BST686T~/`.

Then, in `flask-mijndnamedicatiepas/`:

```sh
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # Windows; use .venv/bin/ on Linux/macOS
```

On Python 3.12+, `locus_processing` needs a newer marshmallow 2.x:

```sh
.venv/Scripts/pip install --no-deps marshmallow==2.21.0
.venv/Scripts/pip install setuptools
```

Build the G-Standaard database (about 150 MB). `-b` is the dated directory of file descriptions
that matches the delivery. Delete an existing `instance/gstandaard.db` first.

```sh
mkdir instance
.venv/Scripts/populate-db -d ../BST686T~ -b ../gstandaard_html_beschrijvingen/20260910 -s instance/gstandaard.db
```

Run the application:

```sh
.venv/Scripts/python app.py
```

## Configuration

| Key | Default |
|---|---|
| `SQLALCHEMY_DATABASE_URI` | `instance/gstandaard.db` |
| `TRANSLATION_TABLES_DIR` | `../koppelingen/vertaling_haplotypes_tsitnrs` |
| `LOCUS_DEFINITIONS` | `../locus_definitions/WES` |

To use other locations, put these keys in a Python file and set `MIJNDNAMEDICATIEPAS_CONF` to its
absolute path.

## Mijn Pas URLs

| Route | Page |
|---|---|
| `/app/<scheme>/<profile>/` | Medicatie: the advice per medicine |
| `/app/<scheme>/<profile>/genoverzicht/` | Genoverzicht: gene, diplotype and phenotype |
| `/app/<scheme>/<profile>/varianten/` | Varianten (v1 profiles only) |
| `/v1/<profile>`, `/v2/<profile>` | The pongs-flask URLs in the QR codes; redirect to the Medicatie page |

`<scheme>` is how the profile is encoded: `v1` (variants, needs the locus definitions) or `v2`
(alleles, indexes into the translation table). An undecodable profile gives a 404.
