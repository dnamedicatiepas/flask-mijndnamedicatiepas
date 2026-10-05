(function (){
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
        return fetch(url, { method: method, headers: headers, body: body}).then(function (res) {
            return res.text();
        })
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
        });
    }

    window.addEventListener("popstate", function () {
        var target = document.querySelector("#page");
        request("GET", location.pathname, null).then(function (html) {
          swap(target, html, "innerHTML");
        });
    });
})