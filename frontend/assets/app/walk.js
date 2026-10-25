// Walking-distance search with Google Places and Routes.
// Used by the tools page (/app), frontend/index.html; runs where the page lists it.

// Walking-distance search: verified homes + Google Places + Google Routes walking times.
(() => {
  if (!document.getElementById('walk-layout')) return;
  const statusEl = document.getElementById('walk-status'),
    layout = document.getElementById('walk-layout');
  const cards = document.getElementById('walk-cards'),
    mapEl = document.getElementById('walk-map'),
    mapText = document.getElementById('walk-map-text');
  const toggle = document.getElementById('walk-toggle');
  const el = (tag, text, attrs = {}) => { const n = document.createElement(tag); if (text != null) n.textContent = text; for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v); return n; };
  const safeUrl = u => typeof u === 'string' && u.startsWith('https://') ? u : null;
  const STATUS = { available_now: 'Available now', advertised_vacancy: 'Vacancy advertised', upcoming: 'Coming soon', leasing: 'Now leasing', waitlist_open: 'Waitlist open', contact_for_availability: 'Contact provider', closed: 'Closed' };
  const walkText = a => a && a.walk_seconds != null ? `${(a.walk_meters / 1609.34).toFixed(1)} mi · ${Math.max(1, Math.round(a.walk_seconds / 60))} min walk` : 'Walking time unavailable';
  const setStatus = (t, state) => { statusEl.textContent = t;
    statusEl.dataset.state = state || ''; };

  // Google Maps loads only if a restricted browser key is configured; otherwise the list still works.
  let gmap = null,
    overlays = [];
  const loadMaps = () => window.clearHomeLoadMaps();

  function directionsUrl(h, a) {
    if (!a || h.lat == null) return null;
    return `https://www.google.com/maps/dir/?api=1&origin=${h.lat},${h.lon}&destination=${a.location.latitude},${a.location.longitude}&travelmode=walking`;
  }
  async function showOnMap(result) {
    const h = result.housing,
      a = result.nearby_amenity;
    mapText.textContent = a ? `${h.name} to ${a.name}: ${walkText(a)}.` : `${h.name}: no nearby place verified.`;
    [...cards.children].forEach(c => c.setAttribute('aria-current', String(c.dataset.id === h.id)));
    try { await loadMaps(); } catch { mapEl.replaceChildren(el('p', 'Map unavailable. Use “Walking directions” to open the route in Google Maps.', { class: 'walk-map-text', style: 'padding:14px' })); return; }
    if (!gmap) gmap = new google.maps.Map(mapEl, {
      center: { lat: 38.85, lng: -77.3 },
      zoom: 11,
      mapTypeControl: true,
      mapTypeControlOptions: {
        style: google.maps.MapTypeControlStyle.HORIZONTAL_BAR,
        position: google.maps.ControlPosition.TOP_LEFT,
        mapTypeIds: ['roadmap', 'satellite']
      },
      streetViewControl: false,
      fullscreenControl: false
    });
    overlays.forEach(o => o.setMap(null));
    overlays = [];
    if (h.lat == null) return;
    const home = { lat: h.lat, lng: h.lon },
      bounds = new google.maps.LatLngBounds(home);
    overlays.push(new google.maps.Marker({
      map: gmap,
      position: home,
      title: `Home: ${h.name}`,
      icon: { path: 'M3 11 12 3l9 8v10h-6v-6H9v6H3z', scale: 1.5, fillColor: '#2f55b5', fillOpacity: 1, strokeColor: '#fff', strokeWeight: 1.6, anchor: new google.maps.Point(12, 21) }
    }));
    if (a) {
      const store = { lat: a.location.latitude, lng: a.location.longitude };
      bounds.extend(store);
      overlays.push(new google.maps.Marker({
        map: gmap,
        position: store,
        title: a.name,
        label: { text: '🛒', fontSize: '13px' },
        icon: { path: google.maps.SymbolPath.CIRCLE, scale: 13, fillColor: '#2f8a4a', fillOpacity: 1, strokeColor: '#fff', strokeWeight: 2 }
      }));
      if (a.walk_seconds != null) {
        try {
          const res = await fetch('/api/housing/route', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ housing_id: h.id, place_id: a.place_id }) });
          if (res.ok) {
            const route = await res.json();
            const path = google.maps.geometry.encoding.decodePath(route.polyline);
            overlays.push(new google.maps.Polyline({ map: gmap, path, strokeColor: '#2f55b5', strokeWeight: 5, strokeOpacity: .85 }));
            path.forEach(p => bounds.extend(p));
          }
        } catch {}
      }
    }
    gmap.fitBounds(bounds, 60);
    google.maps.event.addListenerOnce(gmap, 'idle', () => { if (gmap.getZoom() > 17) gmap.setZoom(17); });
  }

  function card(result) {
    const h = result.housing,
      a = result.nearby_amenity;
    const c = el('article', null, { class: 'walk-card', tabindex: '0', 'data-id': h.id, 'aria-current': 'false' });
    if (h.has_photo) {
      const picture = el('img', null, { alt: `Provider ${h.image_kind === 'rendering' ? 'rendering' : 'photo'} of ${h.name}`, loading: 'lazy', referrerpolicy: 'no-referrer', draggable: 'false' });
      let retried = false;
      picture.addEventListener('error', () => {
        const original = safeUrl(h.photo_url);
        if (!retried && original) { retried = true;
          picture.src = original; return; }
        picture.remove();
        c.classList.add('no-photo');
        const source = safeUrl(h.photo_source_url);
        if (source) body.append(el('a', 'Image unavailable · View official image source ↗', { href: source, target: '_blank', rel: 'noopener noreferrer', class: 'photo-source-notice' }));
      });
      picture.src = listingPhotoSrc(h.id, h.photo_url);
      c.append(picture);
    } else c.classList.add('no-photo');
    const body = el('div');
    body.append(el('h4', h.name));
    if (h.image_kind === 'rendering') body.append(el('div', 'Provider rendering — not a current photo', { class: 'meta' }));
    if (h.photo_license_url && h.photo_credit) {
      const credit = el('div', `Photo: ${h.photo_credit}`, { class: 'photo-attribution' });
      const photoSource = safeUrl(h.photo_source_url),
        license = safeUrl(h.photo_license_url);
      if (photoSource) credit.append(el('a', 'Photo source', { href: photoSource, target: '_blank', rel: 'noopener noreferrer' }));
      if (license) credit.append(el('a', h.photo_license_name || 'Image license', { href: license, target: '_blank', rel: 'noopener noreferrer' }));
      body.append(credit);
    }
    body.append(el('div', [h.address, h.jurisdiction].filter(Boolean).join(' · '), { class: 'meta' }));
    body.append(el('div', h.monthly_rent_display, { class: 'rent' }));
    body.append(el('span', walkText(a), { class: 'walk-badge' + (a && a.walk_seconds != null ? '' : ' na') }));
    if (a) {
      const store = el('div', null, { class: 'walk-store' });
      if (a.photo) store.append(el('img', null, { src: `/api/place-photo?name=${encodeURIComponent(a.photo.name)}`, alt: `Photo of ${a.name}`, loading: 'lazy' }));
      const t = el('div');
      t.append(el('strong', a.name));
      t.append(el('div', a.address || '', { class: 'meta' }));
      if (a.photo && a.photo.attributions?.length) t.append(el('div', 'Photo: ' + a.photo.attributions.map(x => x.name).filter(Boolean).join(', '), { class: 'walk-attr' }));
      store.append(t);
      body.append(store);
    } else body.append(el('div', result.route_status === 'no_coordinates' ? 'No map location on file, so walking time can’t be checked.' : 'No qualifying nearby place was verified.', { class: 'meta' }));
    const ul = el('ul');
    ul.append(el('li', 'Eligibility: ' + (h.eligibility_summary ? h.eligibility_summary.slice(0, 120) : 'Not verified')));
    ul.append(el('li', 'Status: ' + (STATUS[h.availability_status] || 'Status not verified')));
    if (result.match_reasons.length) ul.append(el('li', 'Why it matches: ' + result.match_reasons.join('; ')));
    body.append(ul);
    const actions = el('div', null, { class: 'walk-actions' });
    const src = safeUrl(h.official_source_url);
    if (src) actions.append(el('a', 'Official Source', { href: src, target: '_blank', rel: 'noopener' }));
    const dir = directionsUrl(h, a);
    if (dir) actions.append(el('a', 'Walking Directions', { href: dir, target: '_blank', rel: 'noopener' }));
    const show = el('button', 'Show on Map', { type: 'button' });
    show.addEventListener('click', e => { e.stopPropagation();
      showOnMap(result);
      setView('map'); });
    actions.append(show);
    body.append(actions);
    c.append(body);
    c.addEventListener('click', () => showOnMap(result));
    c.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault();
        showOnMap(result); } });
    return c;
  }

  function setView(view) { if (toggle.hidden) return;
    layout.dataset.view = view;
    toggle.querySelectorAll('button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.view === view))); }
  toggle.addEventListener('click', e => { const b = e.target.closest('button'); if (b) setView(b.dataset.view); });

  // Called by the "Find housing help" form when someone picks a place they want to live near.
  window.clearWalkSearch = () => { setStatus('');
    cards.replaceChildren();
    layout.hidden = true;
    toggle.hidden = true; };
  window.runWalkSearch = async filters => {
    setStatus('Checking verified homes and real walking routes…', 'loading');
    cards.replaceChildren();
    layout.hidden = true;
    toggle.hidden = true;
    try {
      const res = await fetch('/api/housing/search', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ prompt: '', filters }) });
      const data = await res.json();
      if (!res.ok || data.error) throw new Error(data.error || 'Search failed.');
      const f = data.filters || {};
      const label = { supermarket: 'a supermarket', pharmacy: 'a pharmacy', transit: 'a bus or train stop' } [f.amenity];
      setStatus(`${data.results.length} result${data.results.length === 1 ? '' : 's'} in ${f.area}${f.max_rent ? ` under $${Number(f.max_rent).toLocaleString('en-US',{maximumFractionDigits:0})}` : ''} with ${label} within ${f.max_walk_minutes} minutes${f.strict ? '' : ' (preferred)'}.`);
      if (data.warnings?.length) { const ul = el('ul', null, { class: 'walk-warnings' });
        data.warnings.forEach(w => ul.append(el('li', w)));
        statusEl.after(ul);
        setTimeout(() => ul.remove(), 60000); }
      if (data.results.length) {
        data.results.forEach(r => cards.append(card(r)));
        layout.hidden = false;
        toggle.hidden = false;
        setView('list');
        showOnMap(data.results[0]);
      }
      return data.results.length;
    } catch (err) { setStatus(err.message || 'Search failed. Please try again.'); return 0; }
  };
})();
