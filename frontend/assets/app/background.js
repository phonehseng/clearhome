// Background scene: grass, windows lighting up, scroll depth.
// Used by the tools page (/app), frontend/index.html; runs where the page lists it.

// Background: grass blades, windows that light up one by one, and a little depth as the page scrolls.
(() => {
  const scene = document.querySelector('.scene');
  if (!scene) return;
  const grass = scene.querySelector('.sc-grass');
  for (let i = 0; i < 70; i++) {
    const b = document.createElement('i');
    b.className = 'sc-blade';
    b.style.cssText = `--x:${(i * 1.47 + Math.random()).toFixed(2)}cqw;--h:${(1.4 + Math.random() * 1.8).toFixed(2)}cqw;--r:${(Math.random() * 16 - 8).toFixed(1)}deg;--t:${(1.6 + Math.random() * 1.2).toFixed(2)}s;--d:${(-Math.random() * 2).toFixed(2)}s`;
    grass.append(b);
  }
  const still = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const windows = [...scene.querySelectorAll('.sc-win')],
    town = [...scene.querySelectorAll('.sc-town i')];
  windows.forEach((w, i) => w.classList.toggle('lit', i % 2 === 0));
  town.forEach((t, i) => t.style.setProperty('--lit', i % 3 === 0 ? 1 : 0));
  if (!still) setInterval(() => {
    const w = windows[Math.floor(Math.random() * windows.length)];
    w.classList.toggle('lit');
    const t = town[Math.floor(Math.random() * town.length)];
    t.style.setProperty('--lit', t.style.getPropertyValue('--lit') === '1' ? 0 : 1);
  }, 2200);
  if (still) return;
  let ticking = false;
  addEventListener('scroll', () => {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(() => {
      const max = Math.max(1, document.documentElement.scrollHeight - innerHeight);
      scene.style.setProperty('--sy', (scrollY / max * 4).toFixed(3));
      ticking = false;
    });
  }, { passive: true });
})();
