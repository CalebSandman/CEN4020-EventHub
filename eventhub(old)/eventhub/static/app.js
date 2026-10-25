// EventHub client behaviour. No inline scripts (strict CSP). All purchases are
// re-validated server-side; nothing here is trusted.
(function () {
  "use strict";

  // Auto-submit the currency selector.
  document.querySelectorAll("select[data-autosubmit]").forEach(function (sel) {
    sel.addEventListener("change", function () { sel.form.submit(); });
  });

  // Event cards: single click opens the detail page; double click buys one ticket.
  // A browser fires "click" twice before "dblclick", so the single-click action is
  // delayed briefly and cancelled if a double click follows.
  var DELAY_MS = 250;
  document.querySelectorAll(".event-card").forEach(function (card) {
    var timer = null;
    card.addEventListener("click", function (ev) {
      ev.preventDefault();
      if (timer !== null) { return; }
      timer = window.setTimeout(function () {
        timer = null;
        window.location.assign(card.dataset.detailUrl);
      }, DELAY_MS);
    });
    card.addEventListener("dblclick", function (ev) {
      ev.preventDefault();
      if (timer !== null) { window.clearTimeout(timer); timer = null; }
      var form = card.querySelector(".quick-buy-form");
      if (form && !form.dataset.submitted) {
        form.dataset.submitted = "1"; // guard against a third rapid click
        form.submit();
      }
    });
  });
})();
