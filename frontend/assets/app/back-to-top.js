// Back-to-top button for the listings.
// Used by the tools page (/app), frontend/index.html; runs where the page lists it.

// Back to the top of the listings: shown once you've scrolled into the listings, hidden above them and past their end.
(() => {
  const button = document.getElementById('to-top'),
    section = document.getElementById('listings');
  if (!button || !section) return;
  let ticking = false;
  const update = () => {
    ticking = false;
    const r = section.getBoundingClientRect();
    button.classList.toggle('on', r.top < -innerHeight * .4 && r.bottom > innerHeight * .6);
  };
  addEventListener('scroll', () => { if (!ticking) { ticking = true;
      requestAnimationFrame(update); } }, { passive: true });
  addEventListener('resize', update);
  button.addEventListener('click', () => {
    section.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' });
    const heading = document.getElementById('listings-title');
    heading.setAttribute('tabindex', '-1');
    heading.focus({ preventScroll: true });
  });
  update();
})();
