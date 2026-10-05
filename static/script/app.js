(function () {
    var AJAX_HEADERS = { "X-Requested-With": "fetch" };

    function swap(target, html, mode) {
        if (mode === "outerHTML") {
            target.outerHTML = html;
        } else {
            target.innerHTML = html;
        }
    }

    function request(method, url, body) {
        var headers = Object.assign({}, AJAX_HEADERS);
        if (body && !(body instanceof FormData)) {
            headers["Content-Type"] = "application/x-www-form-urlencoded";
        }
        return fetch(url, { method: method, headers: headers, body: body }).then(function (res) {
            return res.text();
        });
    }

    // Marks the nav link that points at the current URL with aria-current="page".
    // Only links carrying `data-nav-link` are touched, style them with [aria-current="page"].
    function syncActiveNav() {
        document.querySelectorAll("[data-nav-link]").forEach(function (link) {
            if (link.pathname === location.pathname) {
                link.setAttribute("aria-current", "page");
            } else {
                link.removeAttribute("aria-current");
            }
        });
    }

    function swapFromEl(el, method, url) {
        var targetSel = el.dataset.target || "#page";
        var swapMode = el.dataset.swap || "innerHTML";
        var push = el.dataset.push === "true";
        var target = document.querySelector(targetSel);
        if (!target) return;

        request(method, url, null).then(function (html) {
            swap(target, html, swapMode);
            if (push) {
                history.pushState({ url: url }, "", url);
            }
            syncActiveNav();
        }).catch(function () {
            // Network error: fall back to a normal full page load.
            location.href = url;
        });
    }

    // Delegated click handler: any <a data-ajax> is fetched and swapped in
    // instead of navigating. Without JS the link still works as a normal link.
    document.addEventListener("click", function (e) {
        var link = e.target.closest("a[data-ajax]");
        if (!link) return;
        // Leave new-tab / download / modified clicks to the browser.
        if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
        if (link.target === "_blank" || link.hasAttribute("download")) return;
        if (link.origin !== location.origin) return;

        e.preventDefault();
        swapFromEl(link, "GET", link.pathname + link.search);
    });

    window.addEventListener("popstate", function () {
        var target = document.querySelector("#page");
        if (!target) return;
        request("GET", location.pathname + location.search, null).then(function (html) {
            swap(target, html, "innerHTML");
            syncActiveNav();
        }).catch(function () {
            location.reload();
        });
    });

    syncActiveNav();
})();
