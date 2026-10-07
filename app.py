from flask import Flask, render_template, request

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


def get_issuer(gen_sequence):
    # Dummy lookup: /app/<issuer slug>/ shows that issuer, anything else LUMC.
    return DUMMY_ISSUERS.get(gen_sequence, DUMMY_ISSUERS["lumc"])


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
# full and AJAX loads alike.
def render_mijn_pas(page, gen_sequence):
    return render_page(f"qr-platform/pages/mijn-pas/{page}.html", page,
                       gen_sequence=gen_sequence, issuer=get_issuer(gen_sequence))


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
@app.route('/app/<gen_sequence>/')
def medication(gen_sequence):
    return render_mijn_pas("medicatie", gen_sequence)


@app.route('/app/<gen_sequence>/genoverzicht/')
def genoverzicht(gen_sequence):
    return render_mijn_pas("genoverzicht", gen_sequence)


@app.route('/app/<gen_sequence>/varianten/')
def varianten(gen_sequence):
    return render_mijn_pas("varianten", gen_sequence)


@app.errorhandler(404)
def not_found(e):
    # No current_page: neither nav tab is the page being shown.
    return render_template("pages/404.html"), 404


if __name__ == "__main__":
    app.run(debug=True)
