import functools
import os
import re

from flask import Flask, render_template, request, abort, redirect, url_for
from markupsafe import Markup

import pongs

app = Flask(__name__)

# The data sources of the PONGS procedure (see pongs.py and the README). The
# defaults expect the G-Standaard database in instance/ and the koppelingen and
# locus_definitions repositories next to this one. A config file named by the
# MIJNDNAMEDICATIEPAS_CONF environment variable (an absolute path) overrides them.
_workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app.config.from_mapping(
    SQLALCHEMY_DATABASE_URI="sqlite:///" + os.path.join(app.instance_path, "gstandaard.db").replace("\\", "/"),
    TRANSLATION_TABLES_DIR=os.path.join(_workspace_dir, "koppelingen", "vertaling_haplotypes_tsitnrs"),
    LOCUS_DEFINITIONS=os.path.join(_workspace_dir, "locus_definitions", "WES"),
)
app.config.from_envvar("MIJNDNAMEDICATIEPAS_CONF", silent=True)
pongs.db.init_app(app)

# Used for <link rel="canonical"> and og:url, which must be absolute.
SITE_URL = "https://mijndnamedicatiepas.nl"

# The "Voor Patiënten" / "Voor Professionals" toggle in the header. `page` is
# matched against the `current_page` a route passes to mark the active tab.
NAV_TABS = [
    {"page": "patienten", "endpoint": "patienten", "label": "Voor Patiënten"},
    {"page": "professionals", "endpoint": "professionals", "label": "Voor Professionals"},
]

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

# The issuers for the "Uw resultaat, uitgegeven door:" card on the Mijn Pas
# pages (qr-platform/partials/issuer_card.html), keyed by the lab encoded in
# the pas: the lab_table values in pongs-translation's translation/variants.py.
# A lab without an entry here (e.g. "University of Florida") shows no card.
#   name     Short name, used in the body text and the button label.
#   logo     Path under static/; a light logo, since the card is dark.
#   logo_alt Full name, read out instead of the logo.
#   website  The issuer's website, opened from the card's button.
ISSUERS = {
    "LUMC": {
        "name": "LUMC",
        "logo": "images/logos/on-dark/lumc.svg",
        "logo_alt": "Leids Universitair Medisch Centrum",
        "website": "https://www.lumc.nl",
    },
    "AmsterdamUMC": {
        "name": "Amsterdam UMC",
        "logo": "images/logos/on-dark/amsterdam-umc.svg",
        "logo_alt": "Amsterdam UMC",
        "website": "https://www.amsterdamumc.nl",
    },
    # Not in lab_table yet.
    "Prinses Máxima Centrum": {
        "name": "Prinses Máxima Centrum",
        "logo": "images/logos/on-dark/prinses-maxima.svg",
        "logo_alt": "Prinses Máxima Centrum",
        "website": "https://www.prinsesmaximacentrum.nl",
    },
    "Maasstad Ziekenhuis": {
        "name": "Maasstad Ziekenhuis",
        "logo": "images/logos/on-dark/maasstad.svg",
        "logo_alt": "Maasstad Ziekenhuis",
        "website": "https://www.maasstadziekenhuis.nl",
    },
}


def get_issuer(pas):
    return ISSUERS.get(pas["lab"])


# The "Uw Adviezen" list on the Medicatie page
# (qr-platform/pages/mijn-pas/medicatie.html), one row per advice in the pas's
# report (see pongs.get_pas()):
#   name         Medication name, the row's title.
#   summary      One-line reason shown under the name.
#   phenotype    The tag on the row; the filter chips are built from these.
#   explanation  Shown when the row is opened.
#   advice       The text in the "Advies" box under the explanation.
# The G-Standaard advice text is HTML: an explanation paragraph followed by the
# advice (usually a list). It is split into explanation and advice when it has
# that shape, else it is all advice.
ADVICE_TEXT = re.compile(r"\s*<p>(?P<explanation>.*?)</p>(?P<advice>.*)", re.DOTALL)


def get_medications(pas):
    medications = []
    for entry in pas["report"]:
        explanation, advice = "", entry["action"]
        match = ADVICE_TEXT.fullmatch(entry["action"])
        if match and match["advice"].strip():
            explanation, advice = match["explanation"], match["advice"]

        medications.append({
            "name": entry["protocol"][:1].upper() + entry["protocol"][1:],
            "summary": entry["pad"],
            "phenotype": entry["phenotype"] or entry["gene"],
            # The G-Standaard text is trusted licensed data; pongs-flask shows it with |safe too.
            "explanation": Markup(explanation),
            "advice": Markup(advice),
        })
    return medications


# Every Mijn Pas page needs the pas, and the SPA navigation loads them one by
# one, so the result of the procedure (~1 s) is kept per profile.
@functools.lru_cache(maxsize=256)
def _get_pas(scheme, encoded_profile):
    return pongs.get_pas(scheme, encoded_profile)


def load_pas(scheme, encoded_profile):
    try:
        return _get_pas(scheme, encoded_profile)
    except pongs.InvalidProfile:
        abort(404)


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
def render_mijn_pas(page, encoded_profile, pas, **context):
    return render_page(f"qr-platform/pages/mijn-pas/{page}.html", page,
                       encoded_profile=encoded_profile, issuer=get_issuer(pas), **context)


@app.context_processor
def inject_globals():
    return {"site_url": SITE_URL, "nav_tabs": NAV_TABS, "faq_items": FAQ_ITEMS, "qr_tabs": QR_TABS}


# The Mijn Pas pages take the profile's scheme (v1 or v2) from the URL. Links
# between them keep the scheme of the current page, so templates only pass
# encoded_profile to url_for().
@app.url_defaults
def add_scheme(endpoint, values):
    if "scheme" in values or not request.view_args or "scheme" not in request.view_args:
        return
    if app.url_map.is_endpoint_expecting(endpoint, "scheme"):
        values["scheme"] = request.view_args["scheme"]


@app.route("/")
def patienten():
    return render_template("pages/patienten.html", current_page="patienten")


@app.route("/voor-professionals/")
def professionals():
    return render_template("pages/professionals.html", current_page="professionals")


# here starts the app routing for the qr platform
# <scheme> is how the profile is encoded: v1 (variants) or v2 (alleles), see pongs.py.
@app.route('/app/<any(v1, v2):scheme>/<encoded_profile>/')
def medication(scheme, encoded_profile):
    pas = load_pas(scheme, encoded_profile)
    return render_mijn_pas("medicatie", encoded_profile, pas, medications=get_medications(pas))


@app.route('/app/<any(v1, v2):scheme>/<encoded_profile>/genoverzicht/')
def genoverzicht(scheme, encoded_profile):
    pas = load_pas(scheme, encoded_profile)
    return render_mijn_pas("genoverzicht", encoded_profile, pas, genes=pas["genes"])


@app.route('/app/<any(v1, v2):scheme>/<encoded_profile>/varianten/')
def varianten(scheme, encoded_profile):
    pas = load_pas(scheme, encoded_profile)
    return render_mijn_pas("varianten", encoded_profile, pas, variants=pas["variants"])


# The QR codes on issued passes point to pongs-flask's /v1/<profile> and
# /v2/<profile>; they open the pas here.
@app.route('/<any(v1, v2):scheme>/<encoded_profile>')
def pongs_profile(scheme, encoded_profile):
    return redirect(url_for("medication", scheme=scheme, encoded_profile=encoded_profile))


@app.errorhandler(404)
def not_found(e):
    # No current_page: neither nav tab is the page being shown.
    return render_template("pages/404.html"), 404


if __name__ == "__main__":
    app.run(debug=True)
