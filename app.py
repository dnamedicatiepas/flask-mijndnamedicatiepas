from flask import Flask, render_template, request, Blueprint

app = Flask(__name__)

# Used for <link rel="canonical"> and og:url, which must be absolute.
SITE_URL = "https://mijndnamedicatiepas.nl"

# The "Voor Patiënten" / "Voor Professionals" toggle in the header. `page` is
# matched against the `current_page` a route passes to mark the active tab.
NAV_TABS = [
    {"page": "patienten", "endpoint": "patienten", "label": "Voor Patiënten"},
    {"page": "professionals", "endpoint": "professionals", "label": "Voor Professionals"},
]

FAQ_LOREM = (
    "Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor "
    "incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud "
    "exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat."
)

# The "Veelgestelde Vragen" block, shared by the patients and professionals pages.
FAQ_ITEMS = [
    {"question": "Wie kan mijn gegevens inzien?", "answer": "De patiënt bepaalt zelf wie hij toestemming geeft om de persoonlijke medicatieadviezen in te zien. Op de DNAmedicatiepas wordt niet bijgehouden welke geneesmiddelen worden gebruikt. Dit kan bij door eigen apotheker worden opgevraagd (medicatieoverzicht of medicijnpaspoort)."},
    {"question": "Kan iedereen een medicatiepas krijgen?", "answer": "Op dit moment wordt gewerkt aan het automatiseren van de aanvraag voor de DNAmedicatiepas. Als dit gereed is, zullen nieuwe patienten van de klinische genetica van het Amsterdam UMC en hun ouders, die een uitgebreide DNA-analyse krijgen, standaard worden gevraagd of zij een DNAmedicatiepas willen."},
    {"question": "Hoe vraag ik een pas aan?", "answer": "U kunt niet zelf een pas aanvragen. De klinisch geneticus biedt u de DNAmedicatiepas aan wanneer een uitgebreide DNA-analyse moet worden uitgevoerd."},
    {"question": "Moet ik betalen voor een pas?", "answer": "De kosten van ca 500 euro worden vergoed door de zorgverzekeraar en belasten het jaarlijkse eigen risico."},
    {"question": "Is mijn kaart beveiligd?", "answer": "Door middel van een QR-code zijn uw relevante DNA-gegevens op uw DNAmedicatiepas beveiligd. Gegevens die in het informatiesysteem van uw (huis)arts of apotheek worden opgeslagen zijn ook beveiligd."},
]

QR_NAV = [
    {"key": "medicatie", "label": "Medicatie", "endpoint": "medication"},
    {"key": "genoverzicht", "label": "Genoverzicht", "endpoint": "genoverzicht"},
    {"key": "varianten", "label": "Varianten", "endpoint": "varianten"},
]

# The "Mijn Pas" / "Informatie & Contact" toggle in the QR-platform header.
# `page` is matched against `current_page` to mark the active tab. An endpoint
# of None renders the tab without a link (section not built yet).
QR_TABS = [
    {"page": "pas", "endpoint": "medication", "label": "Mijn Pas"},
    {"page": "contact", "endpoint": None, "label": "Informatie & Contact"},
]

# DUMMY DATA for the "Uw resultaat, uitgegeven door:" card on the Mijn Pas pages
# (qr-platform/partials/issuer_card.html), keyed by issuer slug. Replace
# get_issuer() with the real lookup once the pas data is available.
#   name     Short name, used in the body text and the button label.
#   logo     Path under static/; a light logo, since the card is dark.
#   logo_alt Full name, read out instead of the logo.
#   website  The issuer's website, opened from the card's button.
DUMMY_ISSUERS = {
    "lumc": {
        "name": "LUMC",
        "logo": "images/logos/on-dark/lumc.svg",
        "logo_alt": "Leids Universitair Medisch Centrum",
        "website": "https://www.lumc.nl",
    },
    "amsterdam-umc": {
        "name": "Amsterdam UMC",
        "logo": "images/logos/on-dark/amsterdam-umc.svg",
        "logo_alt": "Amsterdam UMC",
        "website": "https://www.amsterdamumc.nl",
    },
    "prinses-maxima": {
        "name": "Prinses Máxima Centrum",
        "logo": "images/logos/on-dark/prinses-maxima.svg",
        "logo_alt": "Prinses Máxima Centrum",
        "website": "https://www.prinsesmaximacentrum.nl",
    },
    "maasstad": {
        "name": "Maasstad Ziekenhuis",
        "logo": "images/logos/on-dark/maasstad.svg",
        "logo_alt": "Maasstad Ziekenhuis",
        "website": "https://www.maasstadziekenhuis.nl",
    },
}


def get_issuer(encoded_profile):
    # Dummy lookup: /app/<issuer slug>/ shows that issuer, anything else LUMC.
    return DUMMY_ISSUERS.get(encoded_profile, DUMMY_ISSUERS["lumc"])


# DUMMY DATA for the "Uw Adviezen" list on the Medicatie page
# (qr-platform/pages/mijn-pas/medicatie.html). Replace get_medications() with
# the real lookup once the pas data is available.
#   name         Medication name, the row's title.
#   summary      One-line reason shown under the name.
#   phenotype    The tag on the row; the filter chips are built from these.
#   explanation  Shown when the row is opened.
#   advice       The text in the "Advies" box under the explanation.
# Only Escitalopram has real text (from the design); the rest is placeholder.
DUMMY_MEDICATIONS = [
    {"name": "Clopidogrel", "phenotype": "Poor metabolizer"},
    {
        "name": "Escitalopram",
        "phenotype": "Poor metabolizer",
        "explanation": (
            "Het risico op omzetting van de patiënt naar een ander antidepressivum is verhoogd. "
            "Daarnaast is het risico op QT- verlenging en torsade de pointes in theorie verhoogd, "
            "doordat de genvariatie tot een toename van de plasmaconcentratie van escitalopram leidt. "
            "Bij volgen van onderstaand dosisadvies worden de verhoogde plasmaconcentratie en daarmee "
            "het theoretisch verhoogde risico op QT-verlenging en het verhoogde risico op omzetting van "
            "de patiënt naar een ander antidepressivum teniet gedaan."
        ),
        "advice": (
            "Geef maximaal de volgende doseringen (50% van de normale maximumdosering): "
            "volwassenen tot 65 jaar 10 mg/dag, vanaf 65 jaar 5 mg/dag"
        ),
    },
    {"name": "Flucytosine", "phenotype": "Genactiviteitsscore 1"},
    {"name": "Fluorouracil/Capecitabine", "phenotype": "Genactiviteitsscore 1"},
    {"name": "Imipramine", "phenotype": "Poor metabolizer"},
    {"name": "Mavacamten", "phenotype": "Poor metabolizer"},
    {"name": "Rosuvastatine", "phenotype": "521CC"},
    {"name": "Tegafur", "phenotype": "Genactiviteitsscore 1"},
]
for _medication in DUMMY_MEDICATIONS:
    _medication.setdefault("summary", "Er is een Contraindicatie CYP2C19")
    _medication.setdefault("explanation", FAQ_LOREM)
    _medication.setdefault("advice", FAQ_LOREM)


def get_medications(encoded_profile):
    # Dummy lookup: every pas shows the same list.
    return DUMMY_MEDICATIONS


# DUMMY DATA for the gene table on the Genoverzicht page
# (qr-platform/pages/mijn-pas/genoverzicht.html). Replace get_genes() with the
# real lookup once the pas data is available.
#   gene       Gene name, the row's first column.
#   diplotype  The two alleles, e.g. "*1/*1".
#   phenotype  The resulting phenotype, right-aligned in the last column.
# The values are copied from the design.
DUMMY_GENES = [
    {"gene": "CYP2B6", "diplotype": "*1/*1", "phenotype": "CYP2B6 Normal Metaboliser"},
    {"gene": "CYP2C19", "diplotype": "*2/*2", "phenotype": "CYP2C19 Poor Metaboliser"},
    {"gene": "CYP2C9", "diplotype": "*1/*1", "phenotype": "CYP2C9 *1/*1"},
    {"gene": "CYP3A5", "diplotype": "*3/*3", "phenotype": "CYP3A5 Non-expresser (meest voorkomend)"},
    {"gene": "DPYD", "diplotype": "*1/*13", "phenotype": "DPD Genactiviteitssore 1"},
    {"gene": "HLA-B", "diplotype": "wt/wt", "phenotype": "HLA-B*5701-Negatief"},
    {"gene": "SLCO1B1", "diplotype": "*5/*5", "phenotype": "SLCO1B1 521CC"},
    {"gene": "VKORC1", "diplotype": "wt/wt", "phenotype": "VKORC1-1639GG (1173CC) (wild type)"},
]

DUMMY_VARIANTS = [
    {"gen": "CYP2B6", "covered": ["rs2279343", "rs28399499", "rs3745274", "rs3211371"]},
    {"gen": "SYP2C19", "allele a": "rs4244285", "allele b": "rs4244285", "covered": ["rs12248560", "rs17884712", "rs28399504", "rs41291556", "rs4244285", "rs4986893", "rs56337013", "rs6413438", "rs72552267"]},
    {"gen": "CYP2C9", "covered": ["rs1057910", "rs1799853", "rs28371685", "rs28371686"]},
    {"gen": "CYP3A5", "covered": ["rs10264272", "rs41303343", "rs776746"]},
    {"gen": "DPYD", "allele b": "rs55886062", "covered": ["rs3918290", "rs55886062", "rs56038477", "rs67376798"]},
    {"gen": "HLA-B", "covered": ["rs2395029"]},
    {"gen": "SLCO1B1", "allele a": "rs4149056", "allele b": "rs4149056", "covered": ["rs4149056"]},
    {"gen": "VKORC1", "covered": ["rs9934438"]}
]


def get_genes(encoded_profile):
    # Dummy lookup: every pas shows the same genes.
    return DUMMY_GENES


# checks if the X-Requested-With is given in the fetch
# If it is, only the inner page fragment gets returned.
# If not, the return will also include the outer template/shell in the response
# `current_page` picks the active header tab (see QR_TABS).
def render_page(template, active_nav, current_page="pas", **context):
    context.update(nav=QR_NAV, active=active_nav, current_page=current_page)
    if request.headers.get("X-Requested-With") == "fetch":
        return render_template(template, **context)
    return render_template("qr-platform/template.html", inner_template=template, **context)


# A Mijn Pas page: qr-platform/pages/mijn-pas/<page>.html, whose nav key is also
# <page>. Each of these pages includes the issuer card, so `issuer` is passed on
# full and AJAX loads alike. Extra keyword arguments are passed to the page.
def render_mijn_pas(page, encoded_profile, **context):
    return render_page(f"qr-platform/pages/mijn-pas/{page}.html", page,
                       encoded_profile=encoded_profile, issuer=get_issuer(encoded_profile), **context)


@app.context_processor
def inject_globals():
    return {"site_url": SITE_URL, "nav_tabs": NAV_TABS, "faq_items": FAQ_ITEMS, "qr_tabs": QR_TABS}


@app.route("/")
def patienten():
    return render_template("pages/patienten.html", current_page="patienten")


@app.route("/voor-professionals/")
def professionals():
    return render_template("pages/professionals.html", current_page="professionals")


# here starts the app routing for the qr platform
# Later the parameter will be encoded with the lab origin as well
# currently it is bound to the literal name of the lab.
@app.route('/app/<encoded_profile>/')
def medication(encoded_profile):
    return render_mijn_pas("medicatie", encoded_profile, medications=get_medications(encoded_profile))


@app.route('/app/<encoded_profile>/genoverzicht/')
def genoverzicht(encoded_profile):
    return render_mijn_pas("genoverzicht", encoded_profile, genes=get_genes(encoded_profile))


@app.route('/app/<encoded_profile>/varianten/')
def varianten(encoded_profile):
    return render_mijn_pas("varianten", encoded_profile)


@app.errorhandler(404)
def not_found(e):
    # No current_page: neither nav tab is the page being shown.
    return render_template("pages/404.html"), 404


if __name__ == "__main__":
    app.run(debug=True)
