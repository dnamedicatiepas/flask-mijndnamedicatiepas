from flask import Flask, render_template

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


@app.context_processor
def inject_globals():
    return {"site_url": SITE_URL, "nav_tabs": NAV_TABS, "faq_items": FAQ_ITEMS}


@app.route("/")
def patienten():
    return render_template("pages/patienten.html", current_page="patienten")


@app.route("/voor-professionals/")
def professionals():
    return render_template("pages/professionals.html", current_page="professionals")


@app.errorhandler(404)
def not_found(e):
    # No current_page: neither nav tab is the page being shown.
    return render_template("pages/404.html"), 404


if __name__ == "__main__":
    app.run(debug=True)
