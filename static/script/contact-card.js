// The hospital dropdown of the contact card on /app/help/
// (templates/qr-platform/partials/contact_card.html).
//
// A disclosure: a button (aria-expanded) that shows a list of links, one per
// hospital. Choosing one fetches that hospital's card from help_contact
// (X-Requested-With: fetch, as spa.js sends) and swaps it into
// #hospital-contact, then says so in the role="status" line (WCAG 4.1.3).
// Without JS the links are normal links to the full page.
//
// Keyboard: Enter/Space or ArrowDown/ArrowUp on the button opens the menu
// (focusing the first/last option), arrows move between options, Escape
// closes and returns to the button. Tabbing out closes it (WCAG 2.1.2).
(function () {
    var root = document.querySelector("[data-hospital-select]");
    if (!root) return;

    var button = root.querySelector("[data-hospital-button]");
    var label = root.querySelector("[data-hospital-label]");
    var menu = root.querySelector("[data-hospital-menu]");
    var status = root.querySelector("[data-hospital-status]");
    var target = root.querySelector("#hospital-contact");
    var options = Array.prototype.slice.call(root.querySelectorAll("[data-hospital-option]"));
    // Only the latest choice may fill the card, if responses arrive out of order.
    var requestId = 0;

    function isOpen() {
        return button.getAttribute("aria-expanded") === "true";
    }

    function open(focusIndex) {
        button.setAttribute("aria-expanded", "true");
        menu.hidden = false;
        if (typeof focusIndex === "number") options[focusIndex].focus();
    }

    function close(returnFocus) {
        if (!isOpen()) return;
        button.setAttribute("aria-expanded", "false");
        menu.hidden = true;
        if (returnFocus) button.focus();
    }

    function choose(option) {
        var name = option.textContent.trim();
        options.forEach(function (other) {
            other.removeAttribute("aria-current");
        });
        option.setAttribute("aria-current", "true");
        label.textContent = name;
        label.classList.add("hospital-select__value--chosen");
        close(true);
        load(option.href, name);
    }

    function load(url, name) {
        var id = ++requestId;
        status.textContent = "";
        target.setAttribute("aria-busy", "true");
        fetch(url, {headers: {"X-Requested-With": "fetch"}}).then(function (res) {
            if (!res.ok) throw new Error(res.status);
            return res.text();
        }).then(function (html) {
            if (id !== requestId) return;
            target.innerHTML = html;
            target.removeAttribute("aria-busy");
            status.textContent = "Contactgegevens van " + name + " worden getoond.";
        }).catch(function () {
            // Network or server error: the same URL as a full page still shows it.
            if (id === requestId) location.href = url;
        });
    }

    button.addEventListener("click", function () {
        if (isOpen()) {
            close(false);
        } else {
            open();
        }
    });

    button.addEventListener("keydown", function (e) {
        if (e.key === "ArrowDown" || e.key === "ArrowUp") {
            e.preventDefault();
            open(e.key === "ArrowDown" ? 0 : options.length - 1);
        }
    });

    menu.addEventListener("click", function (e) {
        var option = e.target.closest("[data-hospital-option]");
        if (!option) return;
        // Leave new-tab / modified clicks to the browser.
        if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
        e.preventDefault();
        choose(option);
    });

    menu.addEventListener("keydown", function (e) {
        var index = options.indexOf(document.activeElement);
        if (e.key === "ArrowDown" || e.key === "ArrowUp") {
            e.preventDefault();
            var step = e.key === "ArrowDown" ? 1 : -1;
            options[(index + step + options.length) % options.length].focus();
        } else if (e.key === "Home" || e.key === "End") {
            e.preventDefault();
            options[e.key === "Home" ? 0 : options.length - 1].focus();
        } else if (e.key === " " && index !== -1) {
            // Space activates buttons, not links; the trigger looks like a
            // select, so let Space choose too.
            e.preventDefault();
            choose(options[index]);
        }
    });

    root.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && isOpen()) {
            e.preventDefault();
            close(true);
        }
    });

    // Focus moved somewhere outside the dropdown (Tab, or a click elsewhere).
    root.addEventListener("focusout", function (e) {
        if (e.relatedTarget && !root.querySelector(".hospital-select").contains(e.relatedTarget)) {
            close(false);
        }
    });

    document.addEventListener("click", function (e) {
        if (!root.querySelector(".hospital-select").contains(e.target)) close(false);
    });
})();
