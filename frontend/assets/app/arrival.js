// Clears the dark-blue arrival from the front page's Gemma intro (runs before first paint).
// Used by the tools page (/app), frontend/index.html; runs where the page lists it.

// Arriving from the front page's Gemma intro (Skip or a first question): the page starts under the intro's dark blue
// and clears through a blur. The one-use marker is read before the first paint, so a reload, a direct visit or
// back/forward never replays it, and a stale one (slow or failed navigation) is ignored.
(() => {
  try {
    const at = Number(sessionStorage.getItem('ch:app-entry'));
    sessionStorage.removeItem('ch:app-entry');
    const age = Date.now() - at;
    if (!at || age < 0 || age > 8000 || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const root = document.documentElement,
      done = () => root.classList.remove('app-entry', 'app-entry-clear');
    let clearing = false;
    const clear = () => { if (clearing) return;
      clearing = true;
      root.classList.add('app-entry-clear');
      setTimeout(done, 900); };
    // Clear as soon as the page is on screen; never wait for the map, fonts or the chat.
    addEventListener('DOMContentLoaded', () => { requestAnimationFrame(() => requestAnimationFrame(clear));
      setTimeout(clear, 150); });
    setTimeout(clear, 2500); // whatever happens, the veil never stays up
    addEventListener('pageshow', e => { if (e.persisted) done(); });
    root.classList.add('app-entry');
  } catch {}
})();
