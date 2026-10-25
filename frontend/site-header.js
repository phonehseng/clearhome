// Header: once you scroll past the top, keep only the "Get Started" button in view.
(() => {
  const header = document.querySelector('.ch-header'); if (!header) return;
  const update = () => header.classList.toggle('scrolled', scrollY > 40);
  addEventListener('scroll', update, { passive: true }); update();
})();

// Get Started (or any link to the tools page) wakes our Gemma GPU, which sleeps when nobody's using it, so it's
// starting up while the person reads the intro or types their first question. Once per page; the call outlives the
// page change.
(() => {
  let woke = false;
  document.addEventListener('click', e => {
    if (woke || !e.target.closest?.('[data-start], .cl-nav-btn, a[href="/app"]')) return;
    woke = true;
    if (!navigator.sendBeacon?.('/api/gemma/warm')) fetch('/api/gemma/warm', { method: 'POST', keepalive: true }).catch(() => {});
  }, true);
})();
