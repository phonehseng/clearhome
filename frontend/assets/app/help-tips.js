// Help tips beside the optional checkboxes.
// Used by the tools page (/app), frontend/index.html; runs where the page lists it.

// Small help tips beside the optional checkboxes: hover/focus shows, tap toggles, Escape or an outside tap closes.
(() => {
  const btns = [...document.querySelectorAll('.find-help')];
  const set = (b, open) => { b.setAttribute('aria-expanded', open);
    document.getElementById(b.getAttribute('aria-controls')).hidden = !open; if (!open) b.dataset.pinned = ''; };
  const closeAll = except => btns.forEach(b => { if (b !== except) set(b, false); });
  btns.forEach(b => {
    // Hover and focus open the tip before a click lands, so a click pins it open; a second click closes it.
    b.addEventListener('click', e => { e.preventDefault();
      closeAll(b); const pin = b.dataset.pinned !== '1';
      set(b, pin);
      b.dataset.pinned = pin ? '1' : ''; });
    b.addEventListener('mouseenter', () => set(b, true));
    b.addEventListener('mouseleave', () => { if (b.dataset.pinned !== '1' && document.activeElement !== b) set(b, false); });
    b.addEventListener('focus', () => set(b, true));
    b.addEventListener('blur', () => set(b, false));
  });
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeAll(); });
  document.addEventListener('pointerdown', e => { if (!e.target.closest('.find-help')) closeAll(); });
})();
