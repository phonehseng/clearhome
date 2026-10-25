// Progress bar, parallax, word-by-word headings, CTA glow.
// Used by the front page (/), frontend/about.html; runs where the page lists it.

// Scroll-driven extras: progress bar, legacy parallax, word-by-word headings, CTA glow sweep.
(() => {
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const bar = document.createElement('div');
  bar.className = 'scroll-progress';
  bar.setAttribute('aria-hidden', 'true');
  document.body.prepend(bar);

  // Split headings into words (text nodes only, so the "home." highlight span keeps its style).
  document.querySelectorAll('h1, main h2').forEach(h => {
    let i = 0;
    const walk = node => [...node.childNodes].forEach(child => {
      if (child.nodeType === Node.TEXT_NODE) {
        const frag = document.createDocumentFragment();
        child.textContent.split(/(\s+)/).forEach(part => {
          if (!part) return;
          if (/^\s+$/.test(part)) { frag.append(part); return; }
          const w = document.createElement('span');
          w.className = 'word';
          w.style.setProperty('--i', i++);
          w.textContent = part;
          frag.append(w);
        });
        child.replaceWith(frag);
      } else if (child.nodeType === Node.ELEMENT_NODE) walk(child);
    });
    walk(h);
    h.classList.add('split');
    h.setAttribute('aria-label', h.textContent.replace(/\s+/g, ' ').trim());
  });
  const wordsObserver = new IntersectionObserver(entries => entries.forEach(e => {
    if (e.isIntersecting) { e.target.classList.add('words-in');
      wordsObserver.unobserve(e.target); }
  }), { threshold: 0.2 });
  document.querySelectorAll('.split').forEach(h => wordsObserver.observe(h));

  // Parallax layers: the hero picture drifts and zooms slightly; the hero text moves a little slower.
  const art = document.querySelector('.hero-art');
  const heroText = document.querySelector('.hero > div:first-child');
  art?.classList.add('parallax');
  heroText?.classList.add('parallax');
  const cta = document.querySelector('.cta');
  let ticking = false;

  function update() {
    ticking = false;
    const y = scrollY,
      max = document.documentElement.scrollHeight - innerHeight;
    bar.style.transform = `scaleX(${max > 0 ? Math.min(1, y / max) : 0})`;
    if (y < innerHeight * 1.2) {
      // Grows from its base line only: moving it down slid the houses past the hero's bottom edge, which cut them off flat.
      if (art) art.style.transform = `scale(${1 + Math.min(y, 600) / 6000})`;
      if (heroText) heroText.style.transform = `translate3d(0, ${y * 0.06}px, 0)`;
    }
    if (cta) {
      const r = cta.getBoundingClientRect();
      const p = Math.min(1, Math.max(0, (innerHeight - r.top) / (innerHeight + r.height)));
      cta.style.setProperty('--sweep', p.toFixed(3));
    }
  }
  addEventListener('scroll', () => { if (!ticking) { ticking = true;
      requestAnimationFrame(update); } }, { passive: true });
  addEventListener('resize', update);
  update();
})();
