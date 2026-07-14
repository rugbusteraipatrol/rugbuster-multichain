(() => {
  const termsUrl = "/terms/";
  const styleId = "rb-legal-footer-style";

  function installFooter() {
    if (!document.getElementById(styleId)) {
      const style = document.createElement("style");
      style.id = styleId;
      style.textContent = `
        .rb-legal-footer {
          display:flex !important; flex-wrap:wrap !important; align-items:center !important;
          justify-content:center !important; gap:10px 18px !important; width:100% !important;
          box-sizing:border-box !important; margin-top:48px !important;
          padding:22px max(20px, env(safe-area-inset-right)) calc(22px + env(safe-area-inset-bottom)) max(20px, env(safe-area-inset-left)) !important;
          border-top:1px solid rgba(120,145,170,.28) !important; color:#97a5b5 !important;
          background:rgba(5,8,13,.96) !important; font:11px/1.55 "Share Tech Mono", ui-monospace, monospace !important;
          letter-spacing:.5px !important; text-align:center !important;
        }
        .rb-legal-footer__copy { max-width:760px; }
        .rb-legal-footer__link { color:#60d9ff !important; text-decoration:underline !important; text-underline-offset:3px !important; white-space:nowrap; }
        .rb-legal-footer__link:hover, .rb-legal-footer__link:focus-visible { color:#fff !important; outline:none; }
        @media (max-width:600px) { .rb-legal-footer { margin-top:32px !important; font-size:10px !important; } }
      `;
      document.head.append(style);
    }

    const footer = document.querySelector("footer") || document.body.appendChild(document.createElement("footer"));
    footer.classList.add("rb-legal-footer");
    if (footer.querySelector("[data-rb-legal-link]")) return;

    const copy = document.createElement("span");
    copy.className = "rb-legal-footer__copy";
    copy.textContent = "Informational risk signals only. Not financial, legal, or investment advice.";

    const link = document.createElement("a");
    link.className = "rb-legal-footer__link";
    link.dataset.rbLegalLink = "true";
    link.href = termsUrl;
    link.textContent = "Terms & Disclaimer";
    footer.append(copy, link);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", installFooter, { once: true });
  } else {
    installFooter();
  }
})();
