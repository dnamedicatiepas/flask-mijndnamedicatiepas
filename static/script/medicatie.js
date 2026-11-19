(function () {
    // The phenotype filter on the Medicatie page (qr-platform/pages/mijn-pas/
    // medicatie.html). Delegated on document because spa.js swaps the page in
    // with innerHTML, which never runs scripts inside the fragment.
    // A chip's data-phenotype-filter is the phenotype to show; "" shows all.
    document.addEventListener("click", function (e) {
        var chip = e.target.closest("[data-phenotype-filter]");
        if (!chip) return;

        var group = chip.closest(".med-filter");
        var tables = chip.closest("#information-tables");
        if (!group || !tables) return;

        var phenotype = chip.dataset.phenotypeFilter;

        group.querySelectorAll("[data-phenotype-filter]").forEach(function (other) {
            other.setAttribute("aria-pressed", other === chip ? "true" : "false");
        });

        var shown = 0;
        tables.querySelectorAll(".med-item").forEach(function (item) {
            item.hidden = phenotype !== "" && item.dataset.phenotype !== phenotype;
            if (!item.hidden) shown++;
        });

        // The role="status" line under the chips (WCAG 4.1.3).
        var status = tables.querySelector("[data-phenotype-status]");
        if (status) {
            status.textContent = (shown === 1 ? "1 geneesmiddel" : shown + " geneesmiddelen") + " getoond" +
                (phenotype === "" ? "" : " voor " + phenotype);
        }
    });
})();
