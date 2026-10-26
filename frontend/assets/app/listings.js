// Explore Rentals: listing cards, filters, favorites, sharing, Gemma's sort.
// Used by the tools page (/app), frontend/index.html; runs where the page lists it.

const photoDialog = document.getElementById('property-photo-dialog');
document.getElementById('close-property-photo').addEventListener('click', () => photoDialog.close());
photoDialog.addEventListener('click', event => { if (event.target === photoDialog) { const rect = photoDialog.getBoundingClientRect(); if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) photoDialog.close(); } });
photoDialog.addEventListener('close', () => { document.body.style.overflow = ''; });
const browseForm = document.getElementById('browse-form');
const browseMessage = document.getElementById('browse-message');
const listingsGrid = document.getElementById('listings-grid');
const moreListings = document.getElementById('show-more-listings');
const allListings = document.getElementById('show-all-listings');
let housingRows = [],
  visibleHousingCount = 6,
  browseRequest = null,
  gemmaOrder = null;
// Favorites live in this browser only (no account), saved as the listing itself so they show whatever the filters are.
// Favorites saved before the rename (under the old Clear House key) still load; the next save moves them to the new key.
const FAVORITES_KEY = 'clearhome.favorites',
  OLD_FAVORITES_KEY = 'clearhouse.favorites';
let favorites = {};
try { favorites = JSON.parse(localStorage.getItem(FAVORITES_KEY) ?? localStorage.getItem(OLD_FAVORITES_KEY)) || {}; } catch { favorites = {}; }
// A saved listing must look like a listing (an object with an id, and floor plans as a list when present): anything else,
// from an older version or a damaged save, is dropped and the rest are kept, so Favorites always opens.
const savedListing = row => row && typeof row === 'object' && !Array.isArray(row) && typeof row.id === 'string' && row.id &&
  (row.floor_plans === undefined || (Array.isArray(row.floor_plans) && row.floor_plans.every(p => p && typeof p === 'object' && !Array.isArray(p))));
favorites = favorites && typeof favorites === 'object' && !Array.isArray(favorites) ?
  Object.fromEntries(Object.entries(favorites).filter(([, row]) => savedListing(row))) : {};
let showingFavorites = false;
const shownRows = () => showingFavorites ? Object.values(favorites) : housingRows;
const favoriteCount = document.getElementById('favorite-count');

function saveFavorites() { try { localStorage.setItem(FAVORITES_KEY, JSON.stringify(favorites)); } catch {} favoriteCount.textContent = Object.keys(favorites).length; }

function celebrateFavorite(button) {
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const rect = button.getBoundingClientRect();
  const heart = document.createElement('span');
  heart.className = 'favorite-float';
  heart.setAttribute('aria-hidden', 'true');
  heart.style.left = `${rect.left + rect.width / 2}px`;
  heart.style.top = `${rect.top + rect.height / 2}px`;
  heart.append(button.querySelector('svg').cloneNode(true));
  document.body.append(heart);
  const remove = () => heart.remove();
  heart.addEventListener('animationend', remove, { once: true });
  setTimeout(remove, 1100);
}

function favoriteButton(row) {
  const button = housingElement('button', 'favorite-btn');
  button.type = 'button';
  const draw = () => {
    const saved = Boolean(favorites[row.id]);
    button.setAttribute('aria-pressed', String(saved));
    button.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 20s-7-4.4-9-9a4.8 4.8 0 0 1 9-3 4.8 4.8 0 0 1 9 3c-2 4.6-9 9-9 9Z"/></svg>';
    button.title = saved ? 'Saved. Tap to remove' : 'Save';
    button.setAttribute('aria-label', `${saved ? 'Remove' : 'Save'} ${row.community || row.name} ${saved ? 'from' : 'to'} favorites`);
  };
  button.addEventListener('click', () => {
    const saving = !favorites[row.id];
    if (saving) favorites[row.id] = row;
    else delete favorites[row.id];
    saveFavorites();
    if (saving) celebrateFavorite(button);
    if (showingFavorites) renderHousing();
    else draw();
  });
  draw();
  return button;
}
// "Browse housing" links: a quick (~350 ms) smooth scroll to the listings that keeps the real #listings URL.
// Reduced motion keeps the browser's instant jump; any wheel, touch or key press hands scrolling back to the person.
document.querySelectorAll('a[href="#listings"]').forEach(link => link.addEventListener('click', e => {
  const target = document.getElementById('listings');
  if (!target || e.button || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  e.preventDefault();
  const from = scrollY;
  target.scrollIntoView({ block: 'start', behavior: 'instant' });
  const to = scrollY;
  scrollTo(0, from); // exact end point, even with page zoom
  if (location.hash !== '#listings') history.pushState(null, '', '#listings');
  const finish = () => { if (e.detail === 0) { target.tabIndex = -1;
      target.focus({ preventScroll: true }); } }; // keyboard: continue from the listings
  const start = performance.now(),
    duration = 350;
  let stopped = false;
  const stop = () => { stopped = true; };
  ['wheel', 'touchstart', 'keydown'].forEach(type => addEventListener(type, stop, { once: true, passive: true }));
  const step = now => {
    if (stopped) return;
    const t = Math.min(1, (now - start) / duration),
      ease = 1 - Math.pow(1 - t, 3);
    scrollTo(0, from + (to - from) * ease);
    if (t < 1) requestAnimationFrame(step);
    else {
      ['wheel', 'touchstart', 'keydown'].forEach(type => removeEventListener(type, stop));
      finish(); }
  };
  requestAnimationFrame(step);
}));
// Share copies a link that opens the site with that listing pinned first and highlighted.
let sharedListingId = new URLSearchParams(location.search).get('listing');
const shareToast = document.getElementById('share-toast');
let shareToastTimer;
document.body.append(shareToast); // inside the glass listings section a fixed message is placed against the section, off-screen
function notify(message) { shareToast.textContent = message;
  shareToast.classList.add('show');
  clearTimeout(shareToastTimer);
  shareToastTimer = setTimeout(() => shareToast.classList.remove('show'), 2000); }
async function copyText(text) {
  try { await navigator.clipboard.writeText(text); return true; } catch {}
  const area = document.createElement('textarea');
  area.value = text;
  area.setAttribute('readonly', '');
  area.style.position = 'fixed';
  area.style.opacity = '0';
  document.body.append(area);
  area.select();
  let ok = false;
  try { ok = document.execCommand('copy'); } catch {} area.remove();
  return ok;
}

function shareButton(row) {
  const button = housingElement('button', 'share-btn');
  button.type = 'button';
  button.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3v12M7 8l5-5 5 5M5 13v6a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-6"/></svg>';
  button.title = 'Share: copy link';
  button.setAttribute('aria-label', `Share ${row.community || row.name}: copy a link`);
  button.addEventListener('click', async () => {
    const url = new URL(location.pathname, location.origin);
    url.searchParams.set('listing', row.id);
    notify(await copyText(url.href) ? 'Link copied to clipboard.' : 'Couldn’t copy the link. Try again.');
  });
  return button;
}
const listingTabs = [...document.querySelectorAll('.listing-tabs button')];
listingTabs.forEach(tab => tab.addEventListener('click', () => {
  showingFavorites = tab.dataset.list === 'favorites';
  listingTabs.forEach(t => t.setAttribute('aria-pressed', String(t === tab)));
  document.getElementById('listings').dataset.list = tab.dataset.list;
  visibleHousingCount = 6;
  renderHousing();
}));
saveFavorites();
const statusLabels = { available_now: 'Advertised available now', advertised_vacancy: 'Vacancy advertised · confirm date', upcoming: 'Upcoming availability', leasing: 'Now leasing · confirm a unit', waitlist_open: 'Open waitlist · no immediate placement', contact_for_availability: 'Contact for availability' };
// A listing photo's link carries a short tag made from the photo's address, so when a photo is replaced, browsers
// load the new one instead of the copy they cached under the same link.
function listingPhotoSrc(id, url) {
  let h = 0;
  for (const ch of String(url || '')) h = (h * 31 + ch.charCodeAt(0)) | 0;
  return '/media/listings/' + encodeURIComponent(id) + (url ? '?v=' + (h >>> 0).toString(36) : '');
}
// Placeholder art by kind (public-domain / CC0 photos, see images/CREDITS.md): hotels, shelters, legal aid, other
// programs; homes get the map of their area. Never a photo that could pass for a real listing.
const STOCK = {
  hotel: 'hotel',
  emergency_shelter: 'shelter',
  shelter: 'shelter',
  legal_aid: 'legal',
  rental_assistance: 'help',
  housing_authority: 'help',
  program: 'help',
  other: 'help',
  food_support: 'help'
};

function placeholderArt(kind, place) {
  if (STOCK[kind]) return { url: `/images/stock-${STOCK[kind]}.jpg`, map: false };
  const blacksburg = /blacksburg|christiansburg|radford|montgomery/i.test(place || '');
  return { url: `/images/placeholder-${blacksburg ? 'blacksburg' : 'nova'}.jpg`, map: true };
}
// A small glass-covered banner for the tonight panel's cards.
function stockBanner(kind, place) {
  const art = placeholderArt(kind, place),
    b = document.createElement('div');
  b.className = 'stock-banner' + (art.map ? ' map' : '');
  b.setAttribute('aria-hidden', 'true');
  b.style.setProperty('--thumb', `url("${art.url}")`);
  return b;
}

function housingElement(tag, className, content) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (content !== undefined) node.textContent = content;
  return node;
}
// The card's main action follows the listing's status. A phone number wins for calls; otherwise the provider's own page.
function nextStepLink(row) {
  const status = row.availability?.status || '';
  const hasPhone = Boolean(row.phone && (row.phone.match(/\d/g) || []).length >= 10);
  const web = [row.website, row.source_url].find(u => { try { return new URL(u).protocol === 'https:' && row.source_kind !== 'official_directory'; } catch { return false; } });
  if (!hasPhone && !web) return null;
  const labels = {
    waitlist_open: ['Call to Join Waitlist', 'Join Waitlist'],
    available_now: ['Contact to Apply', 'Apply on Provider Site'],
    advertised_vacancy: ['Contact to Apply', 'Apply on Provider Site'],
    leasing: ['Contact to Apply', 'Apply on Provider Site'],
    upcoming: ['Call About Move-In', 'Check Move-In Date'],
  } [status] || ['Call to Confirm Availability', 'Confirm Availability'];
  const link = housingElement('a', 'next-step', hasPhone ? labels[0] : labels[1]);
  if (hasPhone) link.href = ClearHomeDial(row.phone);
  else { link.href = web;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.append(' ↗'); }
  return link;
}

function sourceLink(url, label) {
  try { const parsed = new URL(url); if (parsed.protocol !== 'https:') return null; } catch { return null; }
  const link = housingElement('a', '', label);
  link.href = url;
  link.target = '_blank';
  link.rel = 'noopener noreferrer';
  return link;
}
// Label a listing's main link by where it actually goes (see backend/source_audit.py).
const SOURCE_LABELS = {
  official_property_page: 'Official Page ↗',
  owner_property_page: 'Owner’s Page ↗',
  property_website: 'Website ↗',
  official_directory: 'County Housing List ↗'
};
const sourceLabel = (row, fallback) => SOURCE_LABELS[row.source_kind] || fallback;
const ROLE_LABELS = { provider: 'Property Website', government: 'Official Government Page', directory: 'Official Directory or List', corroboration: 'Supporting Page' };

function mapLink(row) {
  if (!row.address) return null;
  const link = housingElement('a', '', 'Map ↗');
  link.href = 'https://www.google.com/maps/search/?api=1&query=' + encodeURIComponent(row.address);
  link.target = '_blank';
  link.rel = 'noopener noreferrer';
  return link;
}

function reviewedDate(value) {
  if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return 'not recorded';
  const date = new Date(value + 'T12:00:00');
  return Number.isNaN(date.valueOf()) ? 'not recorded' : date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function rentLabel(row) {
  return ClearHomeRental.price(row);
}

function eligibilityDetails(row) {
  const availability = row.availability || {};
  const details = housingElement('details', 'eligibility-details');
  details.append(housingElement('summary', '', 'Eligibility & Important Details'));
  details.dataset.key = 'eligibility:' + row.id;
  const information = housingElement('div', 'eligibility-grid');
  const groups = [
    ['Housing Category & Program', row.affordability?.program],
    ['Room or Apartment', ClearHomeRental.space(row)],
    ['Lease & Responsibility', [ClearHomeRental.lease(row), row.lease_responsibility].filter(Boolean).join('. ')],
    ['Lease Dates & Payments', [ClearHomeRental.term(row), row.payment_schedule].filter(Boolean).join('. ')],
    ['Who Can Apply', [row.minimum_age ? `Age requirement: ${row.minimum_age} and older.` : null, row.who_it_serves].filter(Boolean).join(' ')],
    ['Before You Apply', row.requirements],
    ['Rent & Additional Costs', row.cost],
    ['Availability & Timing', [statusLabels[availability.status], availability.available_from ? 'Advertised move-in: ' + reviewedDate(availability.available_from) + '.' : null, availability.evidence].filter(Boolean).join(' ')],
    ['Accessibility', row.accessibility_notes || 'Ask the provider about accessible units and features.'],
    ['Confirm with Leasing', row.notes],
    ['Units', row.unit_count ? `${row.unit_count} apartments.` : null],
    ['Utilities', row.utilities_notes || row.utilities || 'Not published by the source. Ask the leasing office which utilities are included.'],
    ['Amenities', Array.isArray(row.amenities) && row.amenities.length ? row.amenities.join(' · ') : 'Not published by the source.'],
    ['Leasing Contact', row.phone || 'Not published by the source.'],
    ['How to Apply or Join the Waitlist', row.application_info || row.how_to_apply || 'Ask the leasing office how to apply.']
  ];
  groups.forEach(([title, text]) => { if (!text) return; const group = housingElement('section', 'eligibility-item');
    group.append(housingElement('h4', '', title), housingElement('p', '', text));
    information.append(group); });
  details.append(information, housingElement('div', 'eligibility-footer', 'The provider makes the final eligibility decision. Confirm costs and availability before applying or paying.'));
  if (row.affordability) { const proof = housingElement('div', 'eligibility-item');
    proof.append(housingElement('h4', '', row.type === 'rental_listing' ? 'Rental Source' : 'Affordability Source'), housingElement('p', '', row.affordability.evidence)); const link = sourceLink(row.affordability.source_url, 'Read Source Evidence ↗'); if (link) proof.append(link);
    information.append(proof); }
  const sourceList = housingElement('section', 'eligibility-item');
  sourceList.append(housingElement('h4', '', 'Sources'));
  const seen = new Set();
  [{ url: row.source_url, role: row.source_kind === 'official_directory' ? 'directory' : 'main' }, ...(row.sources || [])].forEach(src => {
    if (!src.url || seen.has(src.url)) return;
    seen.add(src.url);
    const link = sourceLink(src.url, (src.role === 'main' ? sourceLabel(row, 'Main Source ↗') : (ROLE_LABELS[src.role] || 'Source') + ' ↗'));
    if (link) { const line = housingElement('p', '');
      line.append(link);
      sourceList.append(line); }
  });
  information.append(sourceList);
  return details;
}

// The communities in the order shown: a shared listing, then Gemma's picks, then the chosen sort.
function orderedHousing() {
  const hasPhoto = row => (row.floor_plans?.length ? row.floor_plans : [row]).some(p => p.photo);
  // Listings with a photo always come first; the sort is stable, so the chosen order (like rent low to high) holds within each group.
  const rows = shownRows();
  const rank = row => gemmaOrder?.has(row.id) ? gemmaOrder.get(row.id) : Infinity; // the mini Gemma chat's order, if any
  // The chosen sort holds: with "Lowest advertised rent" photos never move a listing; with "Availability first" a photo
  // only lifts a listing within its own run of the same availability. A shared listing, then Gemma's picks, come first.
  const byPhoto = document.getElementById('browse-sort')?.value === 'recommended' && !showingFavorites;
  const group = new Map();
  let run = -1,
    last = null;
  rows.forEach((row, i) => { const status = row.availability?.status || ''; if (i === 0 || status !== last) { run = i;
      last = status; } group.set(row, run); });
  const position = new Map(rows.map((row, i) => [row, i]));
  const ordered = [...rows].sort((a, b) => (b.id === sharedListingId) - (a.id === sharedListingId) || (rank(a) === rank(b) ? 0 : rank(a) - rank(b)) ||
    (byPhoto ? group.get(a) - group.get(b) || hasPhoto(b) - hasPhoto(a) : 0) || position.get(a) - position.get(b));
  return { rows, ordered };
}
// A card's photo loads only as the card nears the screen: a long list on a phone used to fetch every photo at once.
const photoObserver = 'IntersectionObserver' in window ? new IntersectionObserver(entries => entries.forEach(entry => {
  if (!entry.isIntersecting) return;
  photoObserver.unobserve(entry.target);
  entry.target.loadPhoto?.();
}), { rootMargin: '800px 0px' }) : null;
let housingRun = 0; // a new render stops cards still being added from the last one
function housingCard(row) {
  const plans = row.floor_plans?.length ? row.floor_plans : [row];
  const availability = row.availability || {};
  const statuses = new Set(plans.map(p => p.availability?.status));
  const card = housingElement('article', 'housing-card');
  card.dataset.listingId = row.id;
  if (row.id === sharedListingId) card.classList.add('shared-highlight');
  const photoRow = plans.find(p => p.photo) || row;
  const photo = photoRow.photo;
  const imageLabel = photo?.kind === 'rendering' ? 'provider rendering' : 'photo';
  const photoUrl = listingPhotoSrc(photoRow.id, photo?.url);
  const cardPhotoUrl = photoUrl + (photoUrl.includes('?') ? '&' : '?') + 'w=800';
  let displayedPhotoUrl = photoUrl;
  const safePhoto = photo && sourceLink(photo.url, 'Photo') && sourceLink(photo.source_url, 'Photo source');
  // No photo, or one that won't load: a map of the listing's area under frosted glass (never a picture of another home).
  const mapCover = () => {
    const blacksburg = /blacksburg|christiansburg|radford|montgomery/i.test(`${row.region || ''} ${row.jurisdiction || ''}`);
    card.classList.add('has-photo', 'map-photo');
    card.style.setProperty('--card-photo', `url("/images/placeholder-${blacksburg ? 'blacksburg' : 'nova'}.jpg")`);
    const cover = housingElement('div', 'map-photo-glass');
    cover.setAttribute('role', 'img');
    cover.setAttribute('aria-label', `Map of the ${blacksburg ? 'Blacksburg' : 'Northern Virginia'} area; no photo of this property yet`);
    cover.append(housingElement('small', 'map-photo-credit', 'Map data © Google'));
    card.prepend(cover);
  };
  if (!safePhoto) mapCover();
  if (safePhoto) {
    card.classList.add('has-photo');
    const button = housingElement('button', 'property-photo');
    button.type = 'button';
    button.setAttribute('aria-label', `Enlarge ${imageLabel} of ${row.community || row.name}`);
    button.setAttribute('aria-haspopup', 'dialog');
    // This image is a load/error probe even when the glass-card CSS hides it.
    const image = document.createElement('img');
    image.alt = photo.alt || `Community photo of ${row.community}`;
    image.loading = 'eager';
    image.referrerPolicy = 'no-referrer';
    image.draggable = false;
    button.append(image, housingElement('span', 'photo-expand-mark', photo.kind === 'rendering' ? 'Provider rendering · ⤢' : '⤢'));
    const preview = housingElement('span', 'photo-hover');
    preview.setAttribute('aria-hidden', 'true');
    const large = image.cloneNode();
    large.alt = '';
    large.loading = 'lazy';
    preview.append(large, housingElement('small', '', photo.caption || 'Community photo; actual unit may differ.'));
    button.append(preview);
    image.addEventListener('error', () => {
      // A user's browser can load the same official image if its publisher
      // rejects server downloads. Retry once; never substitute another home.
      if (displayedPhotoUrl === photoUrl && new URL(photo.url).protocol === 'https:') {
        displayedPhotoUrl = photo.url;
        card.style.setProperty('--card-photo', `url(${JSON.stringify(displayedPhotoUrl)})`);
        large.src = displayedPhotoUrl;
        image.src = displayedPhotoUrl;
        if (photoDialog.open && photoDialog.dataset.resourceId === photoRow.id) document.getElementById('property-photo-large').src = displayedPhotoUrl;
        return;
      }
      button.remove();
      mapCover();
      if (photoDialog.open && photoDialog.dataset.resourceId === photoRow.id) { document.getElementById('property-photo-large').hidden = true;
        document.getElementById('property-photo-caption').textContent = 'Image unavailable. Open the official source to view available property images.'; }
    });
    // The card shows a smaller copy; the hover preview and the enlarged photo use the original.
    card.loadPhoto = () => { card.style.setProperty('--card-photo', `url("${cardPhotoUrl}")`);
      image.src = cardPhotoUrl;
      large.src = displayedPhotoUrl; };
    if (photoObserver) photoObserver.observe(card); else card.loadPhoto();
    button.addEventListener('click', () => {
      photoDialog.dataset.resourceId = photoRow.id;
      document.getElementById('property-photo-title').textContent = (row.community || row.name) + (photo.kind === 'rendering' ? ' — provider rendering' : '');
      const large = document.getElementById('property-photo-large');
      large.hidden = false;
      large.src = displayedPhotoUrl;
      large.alt = photo.alt || row.community;
      large.referrerPolicy = 'no-referrer';
      large.draggable = false;
      document.getElementById('property-photo-caption').textContent = photo.caption || 'Community photo; actual unit may differ.';
      const source = document.getElementById('property-photo-source');
      source.replaceChildren();
      if (photo.credit) source.append(housingElement('p', '', photo.credit));
      const link = sourceLink(photo.source_url, 'View image source ↗');
      if (link) source.append(link);
      const license = sourceLink(photo.license_url, photo.license_name || 'Image license');
      if (license) source.append(document.createTextNode(' · '), license);
      photoDialog.showModal();
      document.body.style.overflow = 'hidden';
    });
    card.append(button);
  } // no photo: show nothing rather than a placeholder
  const status = housingElement('span', 'housing-status', statuses.size > 1 ? 'Availability varies by plan' : statusLabels[availability.status] || 'Contact for availability');
  status.dataset.status = statuses.size > 1 ? 'mixed' : availability.status || '';
  const tools = housingElement('div', 'card-tools');
  tools.append(favoriteButton(row), shareButton(row));
  const top = housingElement('div', 'card-top');
  top.append(status, tools);
  card.append(top);
  card.append(housingElement('h3', '', row.community || row.name));
  const categories = new Set(plans.map(p => p.type));
  const category = categories.size > 1 ? 'Affordable & regular options' : row.type === 'rental_listing' ? row.rental_space === 'room' ? 'Student room · regular rental' : 'Regular rental · program status unconfirmed' : row.type === 'housing_authority' ? 'Housing program' : 'Income-restricted housing';
  card.append(housingElement('p', 'housing-category', plans.length === 1 && row.floor_plan ? `${category} · ${row.floor_plan}` : category));
  card.append(housingElement('p', 'housing-location', row.address || [row.city, row.jurisdiction].filter(Boolean).join(' · ')));
  const ages = [...new Set(plans.map(p => p.minimum_age))];
  if (ages.length === 1 && row.minimum_age) card.append(housingElement('p', 'housing-age', `For adults ${row.minimum_age}+`));
  else if (ages.some(Boolean)) card.append(housingElement('p', 'housing-age', 'Some options have age requirements'));
  const rent = housingElement('p', 'housing-rent');
  if (typeof row.monthly_rent === 'number' && Number.isFinite(row.monthly_rent)) {
    rent.textContent = `From $${row.monthly_rent.toLocaleString('en-US',{maximumFractionDigits:0})}`;
    rent.append(housingElement('small', '', ClearHomeRental.period(row)));
  } else rent.textContent = 'Rent: confirm with provider';
  card.append(rent);
  // Condensed: what you get, the move-in note, then one muted line of extras and the rent caveat.
  const space = ClearHomeRental.space(row);
  const shared = row.rental_space === 'room' ? 'shared kitchen & living areas' : '';
  if (space) card.append(housingElement('p', 'housing-plan', [space, shared].filter(Boolean).join(' · ')));
  const term = ClearHomeRental.term(row);
  if (term) card.append(housingElement('p', 'housing-plan', term));
  const lease = ClearHomeRental.lease(row);
  const features = [];
  if (lease && !`${row.floor_plan||''} ${category}`.toLowerCase().includes(lease.toLowerCase())) features.push(lease);
  const bedrooms = [...new Set(plans.map(p => p.bedrooms).filter(b => b != null))].sort((a, b) => a - b);
  if (row.rental_space === 'room') { if (!space) features.push('Shared kitchen & living areas'); } else if (bedrooms.length) features.push(bedrooms.map(b => b === 0 ? 'Studio' : `${b} bed`).join(' / '));
  if (plans.length === 1 && row.bathrooms) features.push(`${row.bathrooms} bath`);
  if (plans.length > 1) features.push(`${plans.length} matching plans`);
  features.push(plans.every(p => p.accessible === true) ? 'Accessible unit documented' : 'Confirm accessibility');
  features.push(typeof row.monthly_rent !== 'number' ? 'Ask for rent & fees' : plans.length > 1 ? 'Lowest starting rent among plans' : 'Fees & utilities may be extra');
  card.append(housingElement('p', 'housing-features', features.join(' · ')));
  if (plans.length > 1) {
    const details = housingElement('details', 'floor-plans-details');
    details.dataset.key = 'plans:' + row.id;
    details.append(housingElement('summary', '', `${plans.length} Floor Plans & Eligibility`));
    const options = housingElement('div', 'floor-plan-list');
    plans.forEach(plan => {
      const option = housingElement('section', 'floor-plan-option');
      option.append(housingElement('h4', '', plan.floor_plan || plan.name));
      option.append(housingElement('p', 'option-price', rentLabel(plan)));
      const planFeatures = [];
      if (plan.rental_space === 'room') planFeatures.push(ClearHomeRental.space(plan));
      else if (plan.bedrooms != null) planFeatures.push(plan.bedrooms === 0 ? 'Studio' : `${plan.bedrooms} bed`);
      if (plan.bathrooms) planFeatures.push(`${plan.bathrooms} bath`);
      if (plan.square_feet) planFeatures.push(`${plan.square_feet.toLocaleString('en-US')} sq ft`);
      option.append(housingElement('p', 'housing-features', planFeatures.join(' · ')));
      option.append(housingElement('p', 'option-status', statusLabels[plan.availability?.status] || 'Contact for availability'));
      if (ClearHomeRental.term(plan)) option.append(housingElement('p', 'housing-plan', ClearHomeRental.term(plan)));
      if (ClearHomeRental.lease(plan)) option.append(housingElement('p', 'housing-features', ClearHomeRental.lease(plan)));
      option.append(eligibilityDetails(plan));
      options.append(option);
    });
    details.append(options);
    card.append(details);
  } else card.append(eligibilityDetails(row));
  const actions = housingElement('div', 'housing-actions');
  const nextStep = nextStepLink(row);
  if (nextStep) actions.append(nextStep);
  // The property's own site comes first; a county list (names, addresses, phones) is labeled as a list, not a property page.
  const ownSite = row.website && row.website !== row.source_url && !['property_website', 'owner_property_page', 'official_property_page'].includes(row.source_kind) && !/\.gov\/|\/DocumentCenter\/|\.pdf($|\?)/i.test(row.website) ? sourceLink(row.website, 'Website ↗') : null;
  if (ownSite) actions.append(ownSite);
  const source = sourceLink(row.source_url, sourceLabel(row, plans.length > 1 ? 'Starting-Price Source ↗' : 'View Source ↗'));
  if (source) { if (row.source_kind === 'official_directory') source.title = 'The county’s list of income-restricted properties, with each one’s address and phone. Call the property to apply.';
    actions.append(source); }
  const map = mapLink(row);
  if (map) actions.append(map);
  const reviewDates = plans.map(p => p.availability?.checked_on || p.last_verified).filter(Boolean).sort();
  const reviewed = reviewDates[0] === reviewDates[reviewDates.length - 1] ? reviewedDate(reviewDates[0]) : `${reviewedDate(reviewDates[0])} – ${reviewedDate(reviewDates[reviewDates.length-1])}`;
  card.append(actions, housingElement('p', 'housing-reviewed', `Source reviewed ${reviewed}`));
  if (safePhoto && photo.license_url) {
    const credit = housingElement('div', 'photo-attribution');
    credit.append(housingElement('span', '', `Photo: ${photo.credit}`));
    const imageSource = sourceLink(photo.source_url, 'Photo source');
    if (imageSource) credit.append(imageSource);
    const license = sourceLink(photo.license_url, photo.license_name || 'Image license');
    if (license) credit.append(license);
    card.append(credit);
  }
  if (card.classList.contains('has-photo')) { // keep details together below the dedicated photo area
    const glass = housingElement('div', 'card-glass');
    [...card.children].filter(n => !n.classList.contains('property-photo') && !n.classList.contains('map-photo-glass')).forEach(n => glass.append(n));
    card.append(glass);
  }
  if (gemmaOrder?.has(row.id)) { card.dataset.gemmaRank = gemmaOrder.get(row.id) + 1;
    card.title = `Gemma's pick #${gemmaOrder.get(row.id) + 1}`; }
  return card;
}
function renderHousing() {
  const expanded = new Set([...listingsGrid.querySelectorAll('details[open]')].map(el => el.dataset.key));
  housingRun++;
  const { rows, ordered } = orderedHousing();
  listingsGrid.replaceChildren(...ordered.slice(0, visibleHousingCount).map(housingCard));
  listingsGrid.querySelectorAll('details').forEach(el => { el.open = expanded.has(el.dataset.key); });
  housingStatus(rows);
}
function housingStatus(rows) {
  moreListings.hidden = visibleHousingCount >= rows.length;
  allListings.hidden = moreListings.hidden || rows.length - visibleHousingCount <= 18; // with 18 or fewer left, Show more already reveals them all
  moreListings.textContent = `Show More Results (${Math.max(0,rows.length-visibleHousingCount)} remaining)`;
  allListings.textContent = 'Show All Results';
  browseMessage.dataset.state = 'success';
  if (showingFavorites) { browseMessage.textContent = rows.length ? `${rows.length} saved listing${rows.length === 1 ? '' : 's'}. Saved on this device only; details are as of when you saved them.` : 'No favorites yet. Select Save on any listing to keep it here for later.'; return; }
  browseMessage.textContent = housingRows.length ? `Showing ${Math.min(visibleHousingCount,housingRows.length)} of ${housingRows.length} communities and waitlists${browseForm.elements.namedItem('age_group')?.value === 'general' ? ' (senior-only housing hidden; change Eligibility to include it)' : ''}.` : 'No current reviewed opportunities match these filters. Try another area or budget. Closed and overdue records are excluded; you can call 211 for local housing support.';
}
async function loadHousing() {
  if (browseRequest) browseRequest.abort();
  const controller = new AbortController();
  browseRequest = controller;
  const timeout = setTimeout(() => controller.abort(), 30000);
  const button = browseForm.querySelector('button');
  button.disabled = true;
  listingsGrid.setAttribute('aria-busy', 'true');
  listingsGrid.replaceChildren();
  moreListings.hidden = true;
  allListings.hidden = true;
  browseMessage.dataset.state = 'loading';
  browseMessage.textContent = 'Looking through reviewed housing opportunities…';
  const params = new URLSearchParams({ group_by: 'community' });
  for (const [key, value] of new FormData(browseForm))
    if (value.trim()) params.set(key, value.trim());
  try {
    const response = await fetch('/api/listings?' + params.toString(), { signal: controller.signal });
    const data = await response.json();
    if (!response.ok || !Array.isArray(data.listings)) throw new Error(data.error || 'We couldn’t load housing opportunities.');
    if (browseRequest !== controller) return;
    // Floor plans arrive holding only what differs from their community card.
    housingRows = data.listings.map(row => row.floor_plans ? { ...row, floor_plans: row.floor_plans.map(plan => ({ ...row, ...plan, floor_plans: undefined })) } : row);
    visibleHousingCount = 6;
    window.clearGemmaSort?.();
    renderHousing();
    const sharedCard = sharedListingId && [...listingsGrid.children].find(c => c.dataset.listingId === sharedListingId);
    if (sharedListingId) setTimeout(() => (sharedCard || document.getElementById('listings')).scrollIntoView({ behavior: 'auto', block: 'start' }), 300); // wait for the page above to settle
    // After someone changes the filters, the map follows the homes that match.
    if (filtersChanged) window.clearHomeMapFocus?.(housingRows, `Map shows the ${housingRows.length} matching communit${housingRows.length === 1 ? 'y' : 'ies'}.`);
  } catch (error) {
    if (browseRequest !== controller) return;
    browseMessage.dataset.state = 'error';
    browseMessage.textContent = error.name === 'AbortError' ? 'Loading took too long. Select Update results to try again.' : 'We couldn’t load the housing catalog. Select Update results to retry. If you just updated the app, restart your local server.';
  } finally { clearTimeout(timeout); if (browseRequest === controller) { button.disabled = false;
      listingsGrid.setAttribute('aria-busy', 'false'); } }
}
const budgetShortcut = document.getElementById('budget-under-1500');
const rentFilter = document.getElementById('browse-rent');

function updateBudgetShortcut() { budgetShortcut.setAttribute('aria-pressed', String(rentFilter.value === '1500')); }
budgetShortcut.addEventListener('click', () => { rentFilter.value = '1500';
  document.getElementById('browse-sort').value = 'rent_asc';
  updateBudgetShortcut();
  browseForm.requestSubmit(); });
rentFilter.addEventListener('input', updateBudgetShortcut);
let filtersChanged = false;
browseForm.addEventListener('submit', event => { event.preventDefault();
  filtersChanged = true;
  sharedListingId = null;
  updateBudgetShortcut();
  loadHousing(); });
// Results update as soon as a filter changes; the rent box waits until typing pauses.
let rentTimer;
browseForm.addEventListener('change', event => { if (event.target !== rentFilter) browseForm.requestSubmit(); });
rentFilter.addEventListener('input', () => { clearTimeout(rentTimer);
  rentTimer = setTimeout(() => browseForm.requestSubmit(), 700); });
// "More filters" shows how many of its filters are changed from the default.
function updateMoreCount() { const changed = [
    ['browse-category', 'all'],
    ['browse-age-group', 'general'],
    ['browse-status', '']
  ].filter(([id, def]) => document.getElementById(id).value !== def).length; const badge = document.getElementById('more-filters-count');
  badge.hidden = !changed;
  badge.textContent = `${changed} on`; }
browseForm.addEventListener('submit', updateMoreCount);
// Active-filter summary: names only the filters that differ from the defaults, so a wrong filter is easy to spot.
const FILTER_DEFAULTS = { location: '', housing_type: 'all', rental_space: 'all', age_group: 'general', status: '', max_rent: '', sort: 'rent_asc' };
const filterSummaryText = document.getElementById('filter-summary-text');
const filterReset = document.getElementById('filter-reset');

function updateFilterSummary() {
  const parts = [];
  for (const [name, def] of Object.entries(FILTER_DEFAULTS)) {
    const field = browseForm.elements.namedItem(name);
    if (!field) continue;
    const value = String(field.value || '').trim();
    if (value === def) continue;
    if (name === 'max_rent') parts.push(`up to $${Number(value).toLocaleString('en-US')} / month`);
    else parts.push(field.tagName === 'SELECT' ? field.options[field.selectedIndex].text : value);
  }
  filterSummaryText.textContent = parts.length ? `Showing: ${parts.join(' · ')}` : 'Showing all supported areas, all housing types and all availability.';
  filterReset.disabled = parts.length === 0;
}
filterReset.addEventListener('click', () => {
  for (const [name, def] of Object.entries(FILTER_DEFAULTS)) { const field = browseForm.elements.namedItem(name); if (field) field.value = def; }
  updateBudgetShortcut();
  browseForm.requestSubmit();
});
browseForm.addEventListener('submit', updateFilterSummary);
updateFilterSummary();
// Mini Gemma chat above the listings: a few lines back, and the best fits move to the top of the list below.
const sortForm = document.getElementById('sort-form'),
  sortInput = document.getElementById('sort-input'),
  sortSend = document.getElementById('sort-send');
const sortReply = document.getElementById('sort-reply'),
  sortText = document.getElementById('sort-text');
const sortSample = document.getElementById('sort-sample'),
  sortReset = document.getElementById('sort-reset'),
  SORT_HELLO = sortText.textContent;
window.clearGemmaSort = () => { gemmaOrder = null;
  sortText.textContent = SORT_HELLO;
  sortSample.hidden = false;
  sortReset.hidden = true;
  delete sortReply.dataset.state; };
sortSample.addEventListener('click', () => { sortInput.value = sortSample.dataset.q;
  sortForm.requestSubmit(); });
sortReset.addEventListener('click', () => { window.clearGemmaSort();
  renderHousing(); });
sortForm.addEventListener('submit', async e => {
  e.preventDefault();
  const question = sortInput.value.trim(),
    ids = shownRows().map(r => r.id);
  if (!question || !ids.length) { sortInput.focus(); return; }
  sortSend.disabled = true;
  sortReply.dataset.state = 'loading';
  sortSample.hidden = true;
  sortReset.hidden = true;
  sortText.textContent = 'Sorting the listings for you…';
  try {
    const res = await fetch('/api/listings/sort', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question, ids }) });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Gemma couldn’t sort these right now. Try again in a minute.');
    gemmaOrder = new Map((data.order || []).map((id, i) => [id, i]));
    visibleHousingCount = Math.max(visibleHousingCount, gemmaOrder.size); // every pick is on screen
    renderHousing();
    sortText.textContent = data.note;
    sortReset.hidden = !gemmaOrder.size;
    document.getElementById('sort-chat').scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' });
  } catch (err) {
    sortText.textContent = err.message || 'Gemma couldn’t sort these right now. Try again in a minute.';
    sortSample.hidden = false;
  } finally { delete sortReply.dataset.state;
    sortSend.disabled = false; }
});

function revealCommunities(count) {
  const firstNewIndex = visibleHousingCount;
  const { rows, ordered } = orderedHousing();
  visibleHousingCount = Math.min(rows.length, visibleHousingCount + count);
  // Only the new cards are added (the ones on screen stay as they are): the first dozen at once so the page can glide
  // to them, the rest a batch at a time so a phone never freezes on a long list.
  const run = ++housingRun;
  const fresh = ordered.slice(firstNewIndex, visibleHousingCount);
  const first = fresh.slice(0, 12).map(housingCard);
  first.forEach((c, i) => { c.classList.add('card-reveal');
    c.style.animationDelay = `${i*35}ms`; });
  listingsGrid.append(...first);
  housingStatus(rows);
  let next = first.length;
  const addMore = () => { if (run !== housingRun || next >= fresh.length) return;
    listingsGrid.append(...fresh.slice(next, next += 24).map(housingCard));
    setTimeout(addMore, 30); };
  setTimeout(addMore, 120);
  const firstNewCard = first[0];
  if (firstNewCard) { firstNewCard.tabIndex = -1;
    firstNewCard.focus({ preventScroll: true });
    firstNewCard.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' }); }
}
moreListings.addEventListener('click', () => revealCommunities(18));
allListings.addEventListener('click', () => revealCommunities(shownRows().length));
const initialFilters = new URLSearchParams(location.search);
for (const key of ['location', 'max_rent', 'rental_space', 'age_group']) { const field = browseForm.elements.namedItem(key); if (field && initialFilters.has(key)) field.value = initialFilters.get(key); }
document.getElementById('blacksburg-student-rooms').addEventListener('click', () => { document.getElementById('browse-location').value = 'Blacksburg';
  document.getElementById('browse-space').value = 'room';
  document.getElementById('browse-age-group').value = 'general';
  document.getElementById('browse-category').value = 'all';
  document.getElementById('browse-status').value = '';
  document.getElementById('browse-sort').value = 'rent_asc';
  rentFilter.value = '1000';
  document.getElementById('location').value = 'Blacksburg';
  document.getElementById('browse-location').dispatchEvent(new Event('change'));
  browseForm.requestSubmit(); });
updateMoreCount();
loadHousing();
const tabs = [...document.querySelectorAll('[role=tab]')];

function selectTab(tab, moveFocus = false) {
  tabs.forEach(t => { const selected = t === tab;
    t.setAttribute('aria-selected', String(selected));
    t.tabIndex = selected ? 0 : -1;
    document.getElementById(t.getAttribute('aria-controls')).hidden = !selected; });
  if (moveFocus) tab.focus();
}
tabs.forEach((tab, index) => {
  tab.addEventListener('click', () => selectTab(tab));
  tab.addEventListener('keydown', event => {
    const keys = ['ArrowRight', 'ArrowLeft', 'Home', 'End'];
    if (!keys.includes(event.key)) return;
    event.preventDefault();
    const next = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : (index + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length;
    selectTab(tabs[next], true);
  });
});
const counts = { situation: 'situation-count' };
document.querySelectorAll('textarea').forEach(input => counts[input.id] && input.addEventListener('input', () => { document.getElementById(counts[input.id]).textContent = `${input.value.length.toLocaleString()} / ${input.maxLength.toLocaleString()}`; }));
document.querySelectorAll('[data-example]').forEach(button => button.addEventListener('click', () => { const input = document.getElementById('situation');
  input.value = button.dataset.example;
  input.dispatchEvent(new Event('input'));
  input.focus(); }));
document.querySelectorAll('form[data-endpoint]').forEach(form => form.addEventListener('submit', async event => {
  event.preventDefault();
  const input = form.querySelector('textarea');
  if (!input.value.trim()) { input.setCustomValidity('Please add a few details before continuing.');
    input.reportValidity();
    input.addEventListener('input', () => input.setCustomValidity(''), { once: true }); return; }
  const button = form.querySelector('button[type=submit]');
  const label = button.querySelector('span');
  const result = form.nextElementSibling;
  button.disabled = true;
  label.textContent = 'Working on it…';
  result.dataset.state = 'loading';
  result.textContent = form.dataset.loading;
  result.setAttribute('aria-busy', 'true');
  let payload;
  if (form.id === 'find-form') {
    const area = document.getElementById('location').value.trim();
    const budget = document.getElementById('budget').value;
    payload = { message: [area ? `Location: ${area}.` : '', budget ? `Maximum monthly budget: $${budget}.` : '', input.value.trim()].filter(Boolean).join('\n') };
  } else payload = { text: input.value.trim() };
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 120000);
  try {
    const response = await fetch(form.dataset.endpoint, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload), signal: controller.signal });
    const data = await response.json();
    if (!response.ok || data.error) throw new Error(data.error || 'We couldn’t complete that request. Please try again.');
    if (!data.answer) throw new Error('No response was returned. Please try again.');
    result.dataset.state = 'success';
    result.textContent = data.answer;
  } catch (error) {
    result.dataset.state = 'error';
    result.textContent = error.name === 'AbortError' ? 'This is taking longer than expected. Please try again. For urgent housing support, call 211.' : error instanceof TypeError || error instanceof SyntaxError ? 'We couldn’t reach the service. Check your connection and try again. For urgent housing support, call 211.' : error.message;
  } finally {
    clearTimeout(timeout);
    button.disabled = false;
    label.textContent = form.dataset.submit;
    result.setAttribute('aria-busy', 'false');
  }
}));
