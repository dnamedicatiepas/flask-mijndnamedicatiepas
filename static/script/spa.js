(function () {
    var AJAX_HEADERS = {"X-Requested-With": "fetch"};

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
        return fetch(url, {method: method, headers: headers, body: body}).then(function (res) {
            // The server sends the new page's <title> along (render_page in app.py).
            var title = res.headers.get("X-Page-Title");
            return res.text().then(function (html) {
                return {html: html, title: title ? decodeURIComponent(title) : null};
            });
        });
    }

    // After a swap: give the document the new page's title (WCAG 2.4.2) and say
    // which page is shown in the role="status" line of qr-platform/template.html
    // (WCAG 4.1.3). Focus stays on the link that was used, so without this a
    // screen reader user would not hear that the content changed.
    function afterSwap(title) {
        if (!title) return;
        document.title = title;
        var status = document.querySelector("[data-spa-status]");
        if (!status) return;
        // Cleared first, so the same text is announced again on a repeat visit.
        status.textContent = "";
        setTimeout(function () {
            status.textContent = title.split(" – ")[0] + " geladen";
        }, 50);
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

        request(method, url, null).then(function (page) {
            swap(target, page.html, swapMode);
            if (push) {
                history.pushState({url: url}, "", url);
            }
            syncActiveNav();
            afterSwap(page.title);
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
        // Already on this page: don't fire a redundant request.
        if (link.pathname === location.pathname && link.search === location.search) return;
        swapFromEl(link, "GET", link.pathname + link.search);
    });

    window.addEventListener("popstate", function () {
        var target = document.querySelector("#page");
        if (!target) return;
        request("GET", location.pathname + location.search, null).then(function (page) {
            swap(target, page.html, "innerHTML");
            syncActiveNav();
            afterSwap(page.title);
        }).catch(function () {
            location.reload();
        });
    });

    syncActiveNav();
})();
