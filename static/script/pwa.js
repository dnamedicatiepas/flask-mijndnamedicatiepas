(function () {
    // The PWA side of the Mijn Pas pages (qr-platform/template.html):
    //   - registers the service worker (static/script/sw.js, served at /app/sw.js)
    //   - remembers this pas as the one /app/ opens (the launcher page)
    //   - asks the service worker to save every tab of this pas for offline use
    //   - shows the offline and install banners (qr-platform/partials/pwa_banners.html)
    //
    // The pas is only known as an opaque URL: body[data-pas-url], written by
    // the server. The encoded profile in it is never decoded here.

    var LAST_PAS_KEY = "mijnpas:last";
    var SYNCED_KEY_PREFIX = "mijnpas:synced:";
    var INSTALL_DISMISSED_KEY = "mijnpas:install-dismissed";

    var script = document.currentScript;
    var pasUrl = document.body.dataset.pasUrl;

    // Storage can be blocked (private mode, site data off): never let that
    // break the page.
    function load(key) {
        try { return localStorage.getItem(key); } catch (e) { return null; }
    }

    function store(key, value) {
        try { localStorage.setItem(key, value); } catch (e) {}
    }

    if (pasUrl) store(LAST_PAS_KEY, pasUrl);

    // ===== Service worker =====
    function cacheThisPas(registration) {
        var worker = registration.active;
        if (!worker || !navigator.onLine || !pasUrl) return;

        // The tabs in the pill nav are this pas's pages, as the server wrote them.
        var urls = [];
        document.querySelectorAll("[data-nav-link]").forEach(function (link) {
            if (urls.indexOf(link.pathname) === -1) urls.push(link.pathname);
        });

        // What the page loaded before the service worker was running (on the
        // first visit): the stylesheets (fonts, icon font) and images.
        var assets = [];
        document.querySelectorAll('link[rel="stylesheet"], img[src]').forEach(function (el) {
            var href = el.href || el.src;
            if (href && assets.indexOf(href) === -1) assets.push(href);
        });

        var channel = new MessageChannel();
        channel.port1.onmessage = function (event) {
            if (event.data && event.data.ok) {
                store(SYNCED_KEY_PREFIX + pasUrl, String(event.data.at));
                updateOfflineBanner();
            }
        };
        worker.postMessage({type: "cache-pas", urls: urls, assets: assets}, [channel.port2]);
    }

    if ("serviceWorker" in navigator && script) {
        window.addEventListener("load", function () {
            navigator.serviceWorker.register(script.dataset.swUrl, {scope: script.dataset.swScope})
                .catch(function () {});
            navigator.serviceWorker.ready.then(cacheThisPas);
        });
    }

    // ===== Offline banner =====
    var offlineBanner = document.querySelector("[data-pwa-offline]");

    function updateOfflineBanner() {
        if (!offlineBanner) return;
        offlineBanner.hidden = navigator.onLine;

        var syncedAt = Number(load(SYNCED_KEY_PREFIX + pasUrl));
        var syncedText = offlineBanner.querySelector("[data-pwa-synced-text]");
        if (syncedAt && syncedText) {
            offlineBanner.querySelector("[data-pwa-synced]").textContent =
                new Date(syncedAt).toLocaleDateString("nl-NL", {day: "numeric", month: "long", year: "numeric"});
            syncedText.hidden = false;
        }
    }

    window.addEventListener("online", function () {
        updateOfflineBanner();
        // Back online: refresh the saved copies.
        if ("serviceWorker" in navigator) navigator.serviceWorker.ready.then(cacheThisPas);
    });
    window.addEventListener("offline", updateOfflineBanner);
    updateOfflineBanner();

    // ===== Install banner =====
    var installBanner = document.querySelector("[data-pwa-install]");
    var deferredPrompt = null;

    function isStandalone() {
        return window.matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;
    }

    // iPhone, iPod and iPad; iPadOS reports itself as a Mac with a touch screen.
    function isIos() {
        return /iPhone|iPad|iPod/.test(navigator.userAgent) ||
            (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
    }

    function showInstallBanner(hint) {
        if (!installBanner || isStandalone() || load(INSTALL_DISMISSED_KEY)) return;
        installBanner.querySelectorAll("[data-pwa-install-hint]").forEach(function (el) {
            el.hidden = el.dataset.pwaInstallHint !== hint;
        });
        installBanner.querySelector("[data-pwa-install-button]").hidden = hint !== "prompt";
        installBanner.hidden = false;
    }

    function hideInstallBanner() {
        if (installBanner) installBanner.hidden = true;
    }

    // Chromium (Android, desktop): the browser says when it can install.
    window.addEventListener("beforeinstallprompt", function (event) {
        event.preventDefault();
        deferredPrompt = event;
        showInstallBanner("prompt");
    });

    window.addEventListener("appinstalled", function () {
        deferredPrompt = null;
        hideInstallBanner();
    });

    // iOS has no install prompt: explain the share menu instead. Only Safari
    // (and, since iOS 16.4, other browsers' share menus) can add to the home
    // screen, so the steps fit every iOS browser.
    if (isIos()) showInstallBanner("ios");

    document.addEventListener("click", function (event) {
        if (event.target.closest("[data-pwa-install-button]") && deferredPrompt) {
            deferredPrompt.prompt();
            // A prompt can be shown only once; the browser fires
            // beforeinstallprompt again later if the patient declined.
            deferredPrompt = null;
            hideInstallBanner();
        } else if (event.target.closest("[data-pwa-install-close]")) {
            store(INSTALL_DISMISSED_KEY, "1");
            hideInstallBanner();
        }
    });
})();
