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

## PWA (installable, offline)

The Mijn Pas pages are a Progressive Web App. A patient can put their pas on the home screen, and
the pages they opened keep working without internet. Only `/app/` is part of the app; the rest of
the site is not.

| Route | |
|---|---|
| `/app/<scheme>/<profile>/manifest.webmanifest` | The web app manifest of one pas. Its `start_url` is that pas's Medicatie page, so the installed app always opens that pas (also on iOS, where a home-screen app does not share storage with Safari). |
| `/app/sw.js` | The service worker (`static/script/sw.js`), served here so it controls `/app/`. |
| `/app/` | Opens the pas last viewed on this device, or asks to scan the QR code. |
| `/app/offline/` | Shown offline for a page that was never saved. |

- The encoded profile is never decoded in the browser. The server writes the pas URL into the
  page (`data-pas-url`) and `static/script/pwa.js` and `sw.js` only store and reload whole URLs, so
  a new profile scheme needs no client changes.
- Pages are network first: online, a patient always sees the current advice. On every full page load
  `pwa.js` asks `sw.js` to save all tabs of the pas (full pages and the SPA fragments), so all of
  them open offline after one visit. Offline, a banner shows the date they were saved.
- `pwa.js` also shows an install banner: an install button where the browser supports it
  (Chrome, Edge, Android), the "Deel → Zet op beginscherm" steps on iPhone and iPad.
- Service workers need HTTPS; `localhost` and `127.0.0.1` are the exception (see "Testing on a
  phone" below).
- The app icons in `static/images/pwa/` are rendered from `static/images/favicon.svg` (192 and 512)
  and `static/images/pwa/icon-maskable.svg` (the maskable 512 and the 180 `apple-touch-icon.png`).

### Updating the app

The installed app is the website itself: there is no app store and no separate build. Deploy as
usual; what a patient sees after a deploy depends on what changed:

| Change | Reaches the patient |
|---|---|
| Templates, routes, page content (HTML) | Immediately when online. Pages are network first; the saved copy is only the offline fallback. |
| CSS, JS, images under `/static/` | One visit late. `sw.js` serves these stale-while-revalidate: the first visit after a deploy uses the saved file and fetches the new one in the background, which is used from the next visit. |
| `static/script/sw.js` | On the next online visit. The browser checks `/app/sw.js` on every visit (it is served with `no-cache`); a changed file installs and takes over right away (`skipWaiting` + `clients.claim`). |
| A new tab in `QR_NAV` | Automatically. `pwa.js` saves every page linked in the pill nav (`[data-nav-link]`), so a new tab is offline after one visit. |
| The manifest (name, icons, colours) | Android: Chrome checks it periodically and updates the installed app, usually within a day. iOS: never; the patient must remove the app and add it again. |
| The marketing site (`/`, `/voor-professionals/`) | Not part of the app; no effect. |

Never change the pattern of the manifest's `id` / `start_url` (the pas's Medicatie URL): Android
would treat it as a different app, and installed apps would keep pointing at the old URL.

Release routine:

1. Deploy.
2. If CSS or JS changed that new HTML depends on, bump `VERSION` in `sw.js` (`"v1"` -> `"v2"`).
   Every phone then drops its saved files and fetches fresh ones on its next online visit.
3. If files must be offline before a patient has ever viewed them, add them to `PRECACHE` in
   `sw.js` and bump `VERSION`. A file missing from the server makes the install fail, so the new
   worker would not take over.

Known weak spots (not fixed yet):

- **New HTML with old CSS/JS for one visit.** Static URLs carry no version, so after a deploy the
  first visit can combine new HTML with the saved old CSS/JS. Fix: version every static URL (e.g.
  `styles.css?v=<modification time>`, added in `app.py` through a `url_defaults` hook for
  `static`), so a changed file gets a new URL and is never served from an old copy.
- **Bumping `VERSION` also deletes the saved pas pages.** All caches, including `pages` and
  `fragments`, are named with `VERSION`. A patient who gets the update and goes offline before the
  pages are saved again loses the offline copy. Fix: give `pages` and `fragments` names that don't
  change with `VERSION`, so an update only replaces CSS, JS and images.

### Testing on a phone

A phone can't use the development server on `localhost`, so it needs an HTTPS tunnel:

```sh
ngrok http 5001          # or: cloudflared tunnel --url http://localhost:5001
```

Open `https://<tunnel>/app/<scheme>/<profile>/` on the phone, use the app once online, then try it
in airplane mode. Install from the banner or the browser menu on Android, or from Safari's share
menu ("Zet op beginscherm") on iPhone.

- ngrok's free plan answers requests without its cookie with a warning page. Browsers fetch the
  manifest without cookies by default, so it got that page instead of the manifest, and Chrome
  never offered to install. The `<link rel="manifest">` in `qr-platform/template.html` therefore
  has `crossorigin="use-credentials"`. If installing still fails behind ngrok, use a Cloudflare
  quick tunnel, which has no warning page.
- A free ngrok URL changes on every start, and an installed app stays tied to the URL it was
  installed from. Use ngrok's free static domain (`ngrok http --url=<domain> 5001`) for longer
  tests.
- A tunnel makes the development server public, including the G-Standaard results it shows. Stop
  it when you're done.
- Android only, without a tunnel: connect the phone over USB with USB debugging on, open
  `chrome://inspect` on the computer and forward port 5001. The phone can then use
  `http://localhost:5001`, which counts as secure.
