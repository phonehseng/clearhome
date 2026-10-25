// Scroll entrances and the diagram's request dot.
// Used by the Google Cloud page (/google-cloud), frontend/google-cloud.html; runs where the page lists it.

// Scroll entrances (see the Motion styles): each item rises in once, when it comes on screen, a beat after the
// sibling before it. The diagram starts its request dots when it's in view.
(() => {
  if (matchMedia('(prefers-reduced-motion: reduce)').matches || !('IntersectionObserver' in window)) return;
  const seen = new IntersectionObserver(entries => entries.forEach(e => {
    if (!e.isIntersecting) return;
    e.target.classList.add('gc-on');
    seen.unobserve(e.target);
  }), { threshold: .15, rootMargin: '0px 0px -8% 0px' });
  document.querySelectorAll('.arch-color-line, main h2:not(#cloud-hero-title), main .sub, .arch-row > *, .stack .node, .arch-support, .svc, .control, .end .btn').forEach(el => {
    const n = [...el.parentElement.children].indexOf(el);
    el.style.setProperty('--d', `${Math.min(n, 5) * .08}s`);
    el.classList.add('gc-reveal');
    seen.observe(el);
  });
  document.querySelectorAll('.arch').forEach(el => seen.observe(el));
})();
