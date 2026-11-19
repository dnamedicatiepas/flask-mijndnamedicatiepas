// The service worker of the Mijn Pas PWA. app.py serves this file at /app/sw.js,
// so it controls everything under /app/ (the Mijn Pas pages, the launcher and
// the offline page) and nothing of the rest of the site.
//
// What it keeps:
//   pages      Full Mijn Pas pages, for a launch or reload without internet.
//   fragments  The same pages as the fragments spa.js swaps into #page
//              (requested with X-Requested-With: fetch). Kept apart from
//              `pages` because both live at the same URL.
//   static     CSS, scripts and images under /static/.
//   cdn        The web fonts and the icon font.
//
// Pages are network first, so a patient online always sees the current
// advice; the cache is only the fallback. pwa.js asks to save every tab of a
// pas (the "cache-pas" message) so all of them work offline after one visit.
//
// Bump VERSION when PRECACHE changes or the caching changes shape: the old
// caches are deleted when the new worker activates.
var VERSION = "v2";
var CACHES = {
    pages: "mijnpas-pages-" + VERSION,
    fragments: "mijnpas-fragments-" + VERSION,
    static: "mijnpas-static-" + VERSION,
    cdn: "mijnpas-cdn-" + VERSION,
};

var OFFLINE_URL = "/app/offline/";

// Saved on install: the launcher, the offline page and what every Mijn Pas
// page needs to render. Issuer logos are cached when a page first shows one.
var PRECACHE = [
    "/app/",
    OFFLINE_URL,
    "/static/styles.css",
    "/static/styles/qr-platform/styles.css",
    "/static/styles/not-found.css",
    "/static/script/spa.js",
    "/static/script/medicatie.js",
    "/static/script/pwa.js",
    "/static/images/logo.svg",
    "/static/images/favicon.svg",
    "/static/images/qr-platform/issuer-circle.svg",
    "/static/images/pwa/icon-192.png",
    "/static/images/pwa/apple-touch-icon.png",
];

// Fonts and the icon font, loaded from other origins by the page <head>.
var CDN_HOSTS = [
    "fonts.googleapis.com",
    "fonts.gstatic.com",
    "fonts.cdnfonts.com",
    "cdn.jsdelivr.net",
];

// How long a page request may take before a saved copy is shown instead.
// A first visit (nothing saved yet) always waits for the network.
var NETWORK_TIMEOUT_MS = 5000;

self.addEventListener("install", function (event) {
    event.waitUntil(
        caches.open(CACHES.static).then(function (cache) {
            // /app/ and the offline page go in `pages`, the rest in `static`.
            var pages = PRECACHE.filter(isAppPage);
            var assets = PRECACHE.filter(function (url) { return !isAppPage(url); });
            return Promise.all([
                cache.addAll(assets),
                caches.open(CACHES.pages).then(function (pageCache) { return pageCache.addAll(pages); }),
            ]);
        }).then(function () {
            return self.skipWaiting();
        })
    );
});

self.addEventListener("activate", function (event) {
    var current = Object.keys(CACHES).map(function (key) { return CACHES[key]; });
    event.waitUntil(
        caches.keys().then(function (names) {
            return Promise.all(names.filter(function (name) {
                return name.indexOf("mijnpas-") === 0 && current.indexOf(name) === -1;
            }).map(function (name) {
                return caches.delete(name);
            }));
        }).then(function () {
            return self.clients.claim();
        })
    );
});

self.addEventListener("fetch", function (event) {
    var request = event.request;
    if (request.method !== "GET") return;
    var url = new URL(request.url);

    if (url.origin === self.location.origin) {
        if (isFragment(request)) {
            event.respondWith(networkFirst(request, CACHES.fragments, null));
        } else if (request.mode === "navigate" && isAppPage(url.pathname)) {
            event.respondWith(networkFirst(request, CACHES.pages, OFFLINE_URL));
        } else if (url.pathname.indexOf("/static/") === 0) {
            event.respondWith(staleWhileRevalidate(request, CACHES.static));
        }
        // Anything else (the manifest, sw.js) goes to the network as usual.
    } else if (CDN_HOSTS.indexOf(url.hostname) !== -1) {
        event.respondWith(staleWhileRevalidate(request, CACHES.cdn));
    }
});

// pwa.js: save these pages (the tabs of the pas on screen) as full pages and
// as fragments, plus the page's stylesheets and images (`assets`), which the
// first visit loaded before this worker ran. Replies {ok, at} on the message
// port when done; `ok` covers the pages only.
self.addEventListener("message", function (event) {
    var data = event.data || {};
    if (data.type !== "cache-pas" || !Array.isArray(data.urls)) return;
    var port = event.ports && event.ports[0];

    var urls = data.urls.filter(function (href) {
        var url = new URL(href, self.location.origin);
        return url.origin === self.location.origin && isAppPage(url.pathname);
    });

    (Array.isArray(data.assets) ? data.assets : []).forEach(function (href) {
        var url = new URL(href, self.location.origin);
        if (url.origin === self.location.origin && url.pathname.indexOf("/static/") === 0) {
            saveAsset(new Request(url.href), CACHES.static);
        } else if (CDN_HOSTS.indexOf(url.hostname) !== -1) {
            saveAsset(new Request(url.href, {mode: "no-cors"}), CACHES.cdn);
        }
    });

    var work = Promise.all(urls.map(function (href) {
        return Promise.all([
            save(new Request(href, {credentials: "same-origin"}), CACHES.pages),
            save(new Request(href, {credentials: "same-origin", headers: {"X-Requested-With": "fetch"}}), CACHES.fragments),
        ]);
    })).then(function (results) {
        var ok = results.every(function (pair) { return pair[0] && pair[1]; });
        if (port) port.postMessage({ok: ok, at: Date.now()});
    }, function () {
        if (port) port.postMessage({ok: false});
    });
    event.waitUntil(work);
});

function isAppPage(path) {
    return path.indexOf("/app/") === 0 && path !== "/app/sw.js" && !/\.webmanifest$/.test(path);
}

function isFragment(request) {
    return request.headers.get("X-Requested-With") === "fetch";
}

// Fetches `request` and stores a successful response. Resolves to whether it
// was stored.
function save(request, cacheName) {
    return fetch(request).then(function (response) {
        // A redirected response can't answer a navigation later on.
        if (!response.ok || response.redirected) return false;
        return caches.open(cacheName).then(function (cache) {
            return cache.put(stripHeaders(request), response).then(function () { return true; });
        });
    }, function () {
        return false;
    });
}

// Stores an asset unless it is cached already (staleWhileRevalidate keeps
// it fresh from then on).
function saveAsset(request, cacheName) {
    return caches.open(cacheName).then(function (cache) {
        return cache.match(request, {ignoreVary: true}).then(function (cached) {
            if (cached) return;
            return fetch(request).then(function (response) {
                if (response.ok || response.type === "opaque") return cache.put(request, response);
            });
        });
    }).catch(function () {});
}

// Cache keys without request headers: the cache name already tells fragments
// from full pages, and a stored X-Requested-With would make Vary matching
// fail for the plain request that looks it up later.
function stripHeaders(request) {
    return new Request(request.url);
}

function networkFirst(request, cacheName, fallbackUrl) {
    return caches.open(cacheName).then(function (cache) {
        var key = stripHeaders(request);
        return cache.match(key, {ignoreVary: true}).then(function (cached) {
            var network = fetch(request).then(function (response) {
                if (response.ok && !response.redirected) cache.put(key, response.clone());
                return response;
            });

            // Nothing saved yet: wait for the network, or fall back.
            if (!cached) {
                return network.catch(function () {
                    return fallback(fallbackUrl);
                });
            }

            // Saved: take the network if it answers in time, else the copy.
            // A slow response still updates the cache when it arrives.
            return new Promise(function (resolve) {
                var timer = setTimeout(function () { resolve(cached); }, NETWORK_TIMEOUT_MS);
                network.then(function (response) {
                    clearTimeout(timer);
                    // A server error (5xx) is worse than yesterday's page.
                    resolve(response.status >= 500 ? cached : response);
                }, function () {
                    clearTimeout(timer);
                    resolve(cached);
                });
            });
        });
    });
}

function fallback(url) {
    if (!url) return Response.error(); // spa.js then does a full page load
    return caches.open(CACHES.pages).then(function (cache) {
        return cache.match(url, {ignoreVary: true});
    }).then(function (response) {
        return response || Response.error();
    });
}

function staleWhileRevalidate(request, cacheName) {
    return caches.open(cacheName).then(function (cache) {
        return cache.match(request, {ignoreVary: true}).then(function (cached) {
            var network = fetch(request).then(function (response) {
                // Opaque (cross-origin no-cors) responses report status 0.
                if (response.ok || response.type === "opaque") cache.put(request, response.clone());
                return response;
            });
            if (cached) {
                network.catch(function () {});
                return cached;
            }
            return network;
        });
    });
}
