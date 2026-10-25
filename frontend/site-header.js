// Header: once you scroll past the top, keep only the "Get Started" button in view.
(() => {
  const header = document.querySelector('.ch-header'); if (!header) return;
  const update = () => header.classList.toggle('scrolled', scrollY > 40);
  addEventListener('scroll', update, { passive: true }); update();
})();
