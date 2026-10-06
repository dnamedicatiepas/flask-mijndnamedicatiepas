from flask import Flask, render_template, request
from markupsafe import escape

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
    {"question": "Wie kan mijn gegevens inzien?", "answer": FAQ_LOREM},
    {"question": "Kan iedereen een medicatiepas krijgen?", "answer": FAQ_LOREM},
    {"question": "Hoe vraag ik een pas aan?", "answer": FAQ_LOREM},
    {"question": "Moet ik betalen voor een pas?", "answer": f"{FAQ_LOREM} {FAQ_LOREM}"},
    {"question": "Is mijn kaart beveiligd?", "answer": FAQ_LOREM},
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


# checks if the X-Requested-With is given in the fetch
# If it is, only the inner page fragment gets returned.
# If not, the return will also include the outer template/shell in the response
# `current_page` picks the active header tab (see QR_TABS).
def render_page(template, active_nav, current_page="pas", **context):
    context.update(nav=QR_NAV, active=active_nav, current_page=current_page)
    if request.headers.get("X-Requested-With") == "fetch":
        return render_template(template, **context)
    return render_template("qr-platform/template.html", inner_template=template, **context)


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
@app.route('/app/<gen_sequence>')
def medication(gen_sequence):
    return render_page("qr-platform/pages/mijn-pas/medicatie.html", "medicatie", gen_sequence=gen_sequence)


@app.route('/app/<gen_sequence>/genoverzicht')
def genoverzicht(gen_sequence):
    return render_page("qr-platform/pages/mijn-pas/genoverzicht.html", "genoverzicht", gen_sequence=gen_sequence)


@app.route('/app/<gen_sequence>/varianten')
def varianten(gen_sequence):
    return render_page("qr-platform/pages/mijn-pas/varianten.html", "varianten", gen_sequence=gen_sequence)


@app.errorhandler(404)
def not_found(e):
    # No current_page: neither nav tab is the page being shown.
    return render_template("pages/404.html"), 404


if __name__ == "__main__":
    app.run(debug=True)
