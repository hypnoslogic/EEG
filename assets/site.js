// EEG for Anaesthetists — band-scheme toggle and mobile menu. No dependencies.
(function () {
  var root = document.documentElement;
  var buttons = document.querySelectorAll("[data-scheme-btn]");

  function setScheme(s, save) {
    root.dataset.scheme = s;
    buttons.forEach(function (b) {
      b.setAttribute("aria-checked", String(b.dataset.schemeBtn === s));
    });
    if (save) {
      try { localStorage.setItem("eeg-scheme", s); } catch (e) { /* storage unavailable: still works for this page */ }
    }
  }

  setScheme(root.dataset.scheme === "lee" ? "lee" : "purdon", false);
  buttons.forEach(function (b) {
    b.addEventListener("click", function () { setScheme(b.dataset.schemeBtn, true); });
    b.addEventListener("keydown", function (e) {
      if (e.key === "ArrowLeft" || e.key === "ArrowRight") {
        var next = b.dataset.schemeBtn === "purdon" ? "lee" : "purdon";
        setScheme(next, true);
        document.querySelector('[data-scheme-btn="' + next + '"]').focus();
        e.preventDefault();
      }
    });
  });

  var toggle = document.querySelector(".nav-toggle");
  var nav = document.getElementById("site-nav");
  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      var open = nav.classList.toggle("open");
      toggle.setAttribute("aria-expanded", String(open));
    });
  }
})();
