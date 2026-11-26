/* Applies assets/config.js to every page: app links, email form, analytics. */
(function () {
  "use strict";
  var c = window.BP_CONFIG || {};
  var app = (c.appUrl || "").replace(/\/+$/, "");

  // Links that should lead into the app once it exists.
  document.querySelectorAll("[data-app-link]").forEach(function (a) {
    if (!app) return;
    a.href = app + a.getAttribute("data-app-link");
    var label = a.getAttribute("data-app-text");
    if (label) a.textContent = label;
  });
  document.querySelectorAll("[data-app-only]").forEach(function (el) {
    el.hidden = !app;
  });

  // Newsletter forms.
  document.querySelectorAll("form[data-newsletter]").forEach(function (form) {
    var note = form.parentElement.querySelector("[data-newsletter-note]");
    if (c.buttondownUser) {
      form.action = "https://buttondown.com/api/emails/embed-subscribe/" +
        encodeURIComponent(c.buttondownUser);
      form.method = "post";
      form.target = "_blank";
    } else {
      form.addEventListener("submit", function (e) {
        e.preventDefault();
        if (note) {
          note.textContent = "The email list is not open yet. Please check back soon.";
          note.hidden = false;
        }
      });
    }
  });

  // Cookie-free analytics.
  if (c.goatcounterCode) {
    var s = document.createElement("script");
    s.async = true;
    s.src = "https://gc.zgo.at/count.js";
    s.setAttribute("data-goatcounter",
      "https://" + c.goatcounterCode + ".goatcounter.com/count");
    document.head.appendChild(s);
  }
})();
