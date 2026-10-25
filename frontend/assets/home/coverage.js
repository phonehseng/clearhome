// 'What's in the list' counts from /api/coverage.
// Used by the front page (/), frontend/about.html; runs where the page lists it.

// Coverage counts from the same reviewed catalog the app serves; the numbers above stay if this fails.
(async () => {
  try {
    const r = await fetch('/api/coverage');
    if (!r.ok) return;
    const c = await r.json();
    document.querySelectorAll('[data-count]').forEach(el => { if (Number.isInteger(c[el.dataset.count])) el.textContent = c[el.dataset.count].toLocaleString('en-US'); });
    const day = new Date(c.as_of + 'T12:00:00');
    if (!isNaN(day)) document.getElementById('coverage-date').textContent = 'as of ' + day.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
  } catch {}
})();
