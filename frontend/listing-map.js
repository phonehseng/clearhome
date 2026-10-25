// Listings map shared by the tools page and the front page: Google Maps (Leaflet fallback), house pins,
// county outlines, Northern Virginia / Blacksburg tabs, neighborhoods, Near me, and live web finds.
  // One Google Maps loader for the listings map and the walking map (the browser key is restricted to our sites).
  window.clearHouseLoadMaps = (() => { let ready = null; return () => ready || (ready = fetch('/api/maps-config').then(r => r.json()).then(cfg => new Promise((resolve, reject) => {
    if (!cfg.browser_key) return reject(new Error('no key'));
    window.__clearHouseMaps = () => resolve();
    const sc = document.createElement('script');
    sc.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(cfg.browser_key)}&libraries=geometry&loading=async&callback=__clearHouseMaps`;
    sc.async = true; sc.onerror = () => reject(new Error('load failed')); document.head.append(sc);
    setTimeout(() => reject(new Error('timeout')), 10000);
  }))); })();
  // Listings map: reviewed listings in blue, live web finds in orange, the chosen area outlined.
  // Google Maps when the browser key works; Leaflet + OpenStreetMap as a fallback so the map never goes blank.
  (() => {
    const mapEl = document.getElementById('listing-map');
    const statusEl = document.getElementById('map-status');
    const webList = document.getElementById('web-results');
    const setStatus = (text, state) => { statusEl.textContent = text; statusEl.dataset.state = state || ''; };
    const el = (tag, text, attrs = {}) => { const n = document.createElement(tag); if (text != null) n.textContent = text; for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v); return n; };
    const safeUrl = u => typeof u === 'string' && u.startsWith('https://') ? u : null;
    const OUTLINE = { color: '#6f8fd6', weight: 1, fill: 0.03 }, HIGHLIGHT = { color: '#2f55b5', weight: 3, fill: 0.12 };
    const HOUSE = 'M3 11 12 3l9 8v10h-6v-6H9v6H3z';
    // What the map shows, kept apart from the map library so a fallback can redraw it.
    const state = { boundaries: null, pins: [], webPins: [], homes: null, selected: null, focused: null };
    // Start on the busiest part of Northern Virginia (Arlington to Fairfax) at a zoom where pins don't overlap.
    const START = { center: { lat: 38.86, lng: -77.19 }, zoom: 11 };
    const REGIONS = { nova: [START.center, START.zoom], blacksburg: [{ lat: 37.2296, lng: -80.4139 }, 13] };
    let view = null;

    function googleView() {
      const map = new google.maps.Map(mapEl, { center: { lat: 38.83, lng: -77.35 }, zoom: 9, mapTypeControl: false, fullscreenControl: false,
        streetViewControl: true, clickableIcons: false, gestureHandling: 'cooperative' });
      const info = new google.maps.InfoWindow(), areas = {}, web = [];
      let all = null;
      const style = f => { const s = f.getProperty('jurisdiction') === state.selected ? HIGHLIGHT : OUTLINE;
        return { strokeColor: s.color, strokeWeight: s.weight, fillColor: s.color, fillOpacity: s.fill, clickable: false }; };
      const pin = (p, list) => {
        const m = new google.maps.Marker({ map, position: { lat: p.lat, lng: p.lon }, title: p.title,
          icon: { path: HOUSE, scale: 1.1, fillColor: p.color, fillOpacity: 1, strokeColor: '#fff', strokeWeight: 1.6, anchor: new google.maps.Point(12, 21) } });
        m.addListener('click', () => { info.setContent(p.popup); info.open({ map, anchor: m }); });
        if (list) list.push(m);
      };
      return {
        outlines(gj) {
          all = new google.maps.LatLngBounds();
          map.data.addGeoJson(gj).forEach(f => {
            const b = new google.maps.LatLngBounds(); f.getGeometry().forEachLatLng(ll => { b.extend(ll); all.extend(ll); });
            areas[f.getProperty('jurisdiction')] = b;
          });
          map.data.setStyle(style);
          if (!state.focused) { map.setCenter(START.center); map.setZoom(START.zoom); }  // start close in, so pins don't pile up
        },
        pin: p => pin(p), webPin: p => pin(p, web),
        clearWeb() { web.splice(0).forEach(m => m.setMap(null)); },
        center(c, zoom) { map.setCenter(c); map.setZoom(zoom); },
        me(lat, lon) {
          if (this._me) this._me.setMap(null);
          this._me = new google.maps.Marker({ map, position: { lat, lng: lon }, title: 'You are here', zIndex: 999,
            icon: { path: google.maps.SymbolPath.CIRCLE, scale: 8, fillColor: '#e0a100', fillOpacity: 1, strokeColor: '#fff', strokeWeight: 3 } });
        },
        focus(points) {
          if (points.length === 1) { map.setCenter({ lat: points[0][0], lng: points[0][1] }); map.setZoom(15); return; }
          const b = new google.maps.LatLngBounds(); points.forEach(([lat, lon]) => b.extend({ lat, lng: lon }));
          map.fitBounds(b, 40); google.maps.event.addListenerOnce(map, 'idle', () => { if (map.getZoom() > 15) map.setZoom(15); });
        },
        select(name) {
          map.data.setStyle(style);
          if (areas[name]) map.fitBounds(areas[name], 12);
          else if (name === 'Blacksburg') { map.setCenter({ lat: 37.2296, lng: -80.4139 }); map.setZoom(13); }
          else if (all) map.fitBounds(all, 10);
        },
      };
    }

    function leafletView() {
      mapEl.replaceChildren();
      const map = L.map(mapEl, { scrollWheelZoom: false, zoomControl: true }).setView([38.83, -77.35], 9);
      L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 18,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' }).addTo(map);
      const areas = {}, web = L.layerGroup().addTo(map); let all = null;
      const style = s => ({ color: s.color, weight: s.weight, fillOpacity: s.fill });
      const icon = color => L.divIcon({ className: 'house-pin', iconSize: [24, 24], iconAnchor: [12, 22], popupAnchor: [0, -20],
        html: `<svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true"><path d="${HOUSE}" fill="${color}" stroke="#fff" stroke-width="1.7" stroke-linejoin="round"/></svg>` });
      const pin = (p, layer) => L.marker([p.lat, p.lon], { icon: icon(p.color), title: p.title, keyboard: true }).bindPopup(p.popup).addTo(layer);
      return {
        outlines(gj) {
          const layer = L.geoJSON(gj, { style: style(OUTLINE), interactive: false }).addTo(map);
          layer.eachLayer(l => { areas[l.feature.properties.jurisdiction] = l; });
          all = layer.getBounds();
          if (!state.focused) map.setView([START.center.lat, START.center.lng], START.zoom);
        },
        pin: p => pin(p, map), webPin: p => pin(p, web),
        clearWeb() { web.clearLayers(); },
        center(c, zoom) { map.setView([c.lat, c.lng], zoom); },
        me(lat, lon) {
          if (this._me) this._me.remove();
          this._me = L.circleMarker([lat, lon], { radius: 8, color: '#fff', weight: 3, fillColor: '#e0a100', fillOpacity: 1 }).bindTooltip('You are here').addTo(map);
        },
        focus(points) {
          if (points.length === 1) { map.setView(points[0], 15); return; }
          map.fitBounds(points, { padding: [30, 30], maxZoom: 15 });
        },
        select(name) {
          Object.values(areas).forEach(a => a.setStyle(style(OUTLINE)));
          const a = areas[name];
          if (a) { a.setStyle(style(HIGHLIGHT)); a.bringToFront(); map.fitBounds(a.getBounds(), { padding: [12, 12] }); }
          else if (name === 'Blacksburg') map.setView([37.2296, -80.4139], 13);
          else if (all) map.fitBounds(all, { padding: [10, 10] });
        },
      };
    }

    function draw(v) {
      view = v;
      if (state.boundaries) v.outlines(state.boundaries);
      state.pins.forEach(v.pin); state.webPins.forEach(v.webPin);
      if (state.me) v.me(...state.me);
      if (state.focused) v.focus(state.focused); else if (state.region) v.center(...REGIONS[state.region]); else if (state.selected) v.select(state.selected);
    }
    function useLeaflet() { if (window.L && !(view && view.leaflet)) { draw(Object.assign(leafletView(), { leaflet: true })); } }
    // A rejected key only shows up after the script loads; Google calls this global, so switch to Leaflet then.
    window.gm_authFailure = useLeaflet;
    window.clearHouseLoadMaps().then(() => draw(googleView())).catch(useLeaflet);

    const addPin = p => { state.pins.push(p); view?.pin(p); };
    const addWebPin = p => { state.webPins.push(p); view?.webPin(p); };
    const clearWeb = () => { state.webPins = []; view?.clearWeb(); };

    fetch('/api/boundaries').then(r => r.json()).then(gj => {
      state.boundaries = gj; view?.outlines(gj);
      if (document.getElementById('browse-location')?.value === 'Blacksburg') selectArea('Blacksburg');
    }).catch(() => {});

    function popup(lines, url, linkText) {
      const box = el('div', null, { class: 'map-popup' });
      lines.filter(Boolean).forEach((t, i) => box.append(el(i === 0 ? 'strong' : 'div', t)));
      const link = safeUrl(url);
      if (link) box.append(el('a', linkText, { href: link, target: '_blank', rel: 'noopener' }));
      return box;
    }
    const STATUS = { available_now: 'Available now', advertised_vacancy: 'Vacancy advertised', upcoming: 'Coming soon', leasing: 'Now leasing', waitlist_open: 'Waitlist open', contact_for_availability: 'Call for availability' };
    fetch('/api/listings?fields=pins').then(r => r.json()).then(data => {
      state.homes = (data.listings || []).filter(l => typeof l.lat === 'number');
      fillHoods(tabs.find(t => t.getAttribute('aria-pressed') === 'true')?.dataset.region || 'nova');
      state.homes.forEach(l => addPin({ lat: l.lat, lon: l.lon, color: '#2f55b5', title: l.community || l.name,
        popup: popup([l.community || l.name, l.floor_plan, typeof l.monthly_rent === 'number' ? ClearHouseRental.price(l) : null,
                      STATUS[l.availability?.status], 'Reviewed by our team'], l.source_url, 'Provider Page') }));
    }).catch(() => {});

    // Same place names the server understands; longest first so "manassas park" wins over "manassas".
    const PLACES = [['blacksburg','Blacksburg'],['virginia tech','Blacksburg'],['manassas park','Manassas Park City'],['manassas','Manassas City'],['falls church','Falls Church City'],['fairfax city','Fairfax City'],['city of fairfax','Fairfax City'],['fairfax','Fairfax County'],['arlington','Arlington County'],['alexandria','Alexandria City'],['loudoun','Loudoun County'],['leesburg','Loudoun County'],['sterling','Loudoun County'],['ashburn','Loudoun County'],['prince william','Prince William County'],['woodbridge','Prince William County'],['dumfries','Prince William County']];
    const areaFor = text => { const t = (text || '').toLowerCase(); return (PLACES.find(([w]) => t.includes(w)) || [])[1] || null; };
    function selectArea(name) { state.selected = name || null; state.focused = null; state.region = null; view?.select(state.selected); markTab(name === 'Blacksburg' ? 'blacksburg' : name ? 'nova' : null); }
    // Tabs above the map: jump between the two service regions, or find homes near where you are.
    const tabs = [...document.querySelectorAll('.map-tab[data-region]')];
    const whereBox = document.getElementById('location');
    const fillWhere = text => { if (whereBox) whereBox.value = text; };  // no change event, so no web search is started
    // Neighborhood centers (approximate) for the dropdown; the server reads the same names.
    const HOODS = {
      nova: [['Fairfax', 38.8462, -77.3064], ['Reston', 38.9586, -77.3570], ['Herndon', 38.9696, -77.3861], ['Chantilly', 38.8943, -77.4311],
             ['Centreville', 38.8404, -77.4289], ['Tysons', 38.9187, -77.2311], ['McLean', 38.9339, -77.1773], ['Vienna', 38.9012, -77.2653],
             ['Falls Church', 38.8823, -77.1711], ['Annandale', 38.8304, -77.1964], ['Springfield', 38.7893, -77.1872], ['Burke', 38.7934, -77.2717],
             ['Arlington (Ballston)', 38.8821, -77.1112], ['Arlington (Crystal City)', 38.8576, -77.0514], ['Arlington (Columbia Pike)', 38.8625, -77.0906],
             ['Alexandria (Old Town)', 38.8048, -77.0469], ['Alexandria (West End)', 38.8130, -77.1260], ['Leesburg', 39.1157, -77.5636], ['Ashburn', 39.0438, -77.4874],
             ['Sterling', 39.0062, -77.4286], ['Manassas', 38.7509, -77.4753], ['Woodbridge', 38.6582, -77.2497], ['Dumfries', 38.5676, -77.3280], ['Gainesville', 38.7957, -77.6139]],
      blacksburg: [['Virginia Tech campus', 37.2284, -80.4234], ['Downtown Blacksburg', 37.2296, -80.4139], ['North Main Street', 37.2480, -80.4180], ['Christiansburg', 37.1299, -80.4089]],
    };
    const hood = document.getElementById('map-hood');
    // Only offer a neighborhood with at least two reviewed communities within 3 miles, so picking one never shows an empty map.
    const milesApart = (a, b, c, d) => { const r = Math.PI / 180, h = Math.sin((c - a) * r / 2) ** 2 + Math.cos(a * r) * Math.cos(c * r) * Math.sin((d - b) * r / 2) ** 2; return 7917.6 * Math.asin(Math.sqrt(h)); };
    const hasHomes = ([, lat, lon]) => !state.homes || new Set(state.homes.filter(p => milesApart(lat, lon, p.lat, p.lon) <= 3).map(p => p.community || p.name)).size >= 2;
    function fillHoods(region) {
      const keep = hood.value;
      hood.replaceChildren(new Option(region === 'blacksburg' ? 'Area…' : 'Neighborhood…', ''));
      HOODS[region].filter(hasHomes).forEach(([name]) => hood.append(new Option(name, name)));
      hood.value = [...hood.options].some(o => o.value === keep) ? keep : '';
    }
    fillHoods('nova');
    hood.addEventListener('change', () => {
      const region = tabs.find(t => t.getAttribute('aria-pressed') === 'true')?.dataset.region || 'nova';
      const pick = HOODS[region].find(([name]) => name === hood.value); if (!pick) return;
      state.region = null; state.selected = null; state.focused = [[pick[1], pick[2]]];
      view?.center({ lat: pick[1], lng: pick[2] }, 13);
      const where = region === 'blacksburg' && !/christiansburg/i.test(pick[0]) ? `${pick[0]}, Blacksburg` : pick[0];
      fillWhere(where); setStatus(`Showing ${pick[0]}.`);
    });
    // The find form's "Pick an area" moves the map here: a region, a neighborhood, or a county outline.
    window.clearHouseMapGoTo = name => {
      if (/^northern virginia$/i.test(name)) return tabs.find(t => t.dataset.region === 'nova')?.click();
      if (/^blacksburg$/i.test(name)) return tabs.find(t => t.dataset.region === 'blacksburg')?.click();
      const key = name.toLowerCase().replace(/ alexandria$/, '');
      for (const region of ['nova', 'blacksburg']) {
        const pick = HOODS[region].find(([n]) => n.toLowerCase().includes(key) || key.includes(n.toLowerCase().split(' (')[0]));
        if (pick) { markTab(region); state.region = null; state.selected = null; state.focused = [[pick[1], pick[2]]]; view?.center({ lat: pick[1], lng: pick[2] }, 13); setStatus(`Showing ${name}.`); return; }
      }
      const area = areaFor(name); if (area) { selectArea(area); setStatus(`Showing ${area}.`); }
    };
    window.clearHouseOfferWebSearch = place => offerWebSearch(place);
    // Which county or city a point falls in, from the same boundary outlines the map draws.
    function areaAt(lat, lon) {
      const inside = (ring) => { let hit = false; for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) { const [xi, yi] = ring[i], [xj, yj] = ring[j]; if ((yi > lat) !== (yj > lat) && lon < (xj - xi) * (lat - yi) / (yj - yi) + xi) hit = !hit; } return hit; };
      for (const f of state.boundaries?.features || []) {
        const g = f.geometry; const polys = g.type === 'Polygon' ? [g.coordinates] : g.type === 'MultiPolygon' ? g.coordinates : [];
        if (polys.some(p => inside(p[0]))) return f.properties.jurisdiction;
      }
      return Math.hypot(lat - 37.23, lon + 80.42) < 0.25 ? 'Blacksburg' : null;
    }
    const markTab = region => { if (region) tabs.forEach(t => t.setAttribute('aria-pressed', String(t.dataset.region === region))); };
    tabs.forEach(t => t.addEventListener('click', () => {
      state.region = t.dataset.region; state.focused = null; state.selected = null; markTab(state.region);
      view?.center(...REGIONS[state.region]); fillHoods(state.region);
      fillWhere(state.region === 'blacksburg' ? 'Blacksburg' : 'Northern Virginia');
      setStatus(state.region === 'blacksburg' ? 'Showing Blacksburg and Virginia Tech.' : 'Showing Northern Virginia. Pick or type an area to zoom in.');
    }));
    const nearBtn = document.getElementById('near-me');
    nearBtn?.addEventListener('click', () => {
      if (!navigator.geolocation) { setStatus('Your browser can’t share your location. Type a place in the chat instead, like “near my office at …”.'); return; }
      nearBtn.setAttribute('aria-busy', 'true'); setStatus('Finding your location…', 'loading');
      navigator.geolocation.getCurrentPosition(pos => {
        nearBtn.removeAttribute('aria-busy');
        // Rounded to about 100 m before it leaves the browser; it isn't stored.
        const lat = Math.round(pos.coords.latitude * 1000) / 1000, lon = Math.round(pos.coords.longitude * 1000) / 1000;
        state.me = [lat, lon]; view?.me(lat, lon);
        const here = areaAt(lat, lon);  // fill "Where are you looking?" with the county or city you're in
        if (here) { fillWhere(here); markTab(here === 'Blacksburg' ? 'blacksburg' : 'nova'); fillHoods(here === 'Blacksburg' ? 'blacksburg' : 'nova'); }
        state.focused = [[lat, lon]]; view?.center({ lat, lng: lon }, 13); setStatus('Showing homes near you.');
        if (window.clearHouseAsk) window.clearHouseAsk('Homes near my current location', { coords: { lat, lon } });
        else {  // front page: no chat, so fit the map to the 8 closest reviewed homes
          const near = state.pins.map(p => [Math.hypot(p.lat - lat, (p.lon - lon) * Math.cos(lat * Math.PI / 180)), p]).sort((a, b) => a[0] - b[0]).slice(0, 8);
          if (near.length) { state.focused = [[lat, lon], ...near.map(([, p]) => [p.lat, p.lon])]; view?.focus(state.focused); setStatus('Showing the 8 closest reviewed homes to you. Tap a pin for details.'); }
        }
      }, err => {
        nearBtn.removeAttribute('aria-busy');
        setStatus(err.code === 1 ? 'Location is off for this site. Allow it in your browser, or type a place in the chat.' : 'We couldn’t find your location. Try again, or type a place in the chat.');
      }, { enableHighAccuracy: false, timeout: 10000, maximumAge: 300000 });
    });
    // Other parts of the page point the map at what they're showing: the places in Gemma's answer, or filter results.
    window.clearHouseMapFocus = (rows, note) => {
      const points = (rows || []).filter(r => typeof r.lat === 'number' && typeof r.lon === 'number').map(r => [r.lat, r.lon]).slice(0, 60);
      if (!points.length) return;
      state.focused = points; view?.focus(points);
      if (note) setStatus(note);
    };

    let searchId = 0;
    async function liveSearch(location) {
      const id = ++searchId; clearWeb(); webList.hidden = true; webList.replaceChildren();
      setStatus(`Gemma is searching the web for affordable listings in ${location}. This can take a minute…`, 'loading');
      try {
        const controller = new AbortController(); setTimeout(() => controller.abort(), 180000);
        const res = await fetch('/api/live-search', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ location }), signal: controller.signal });
        const data = await res.json();
        if (id !== searchId) return;
        if (!res.ok || data.error) throw new Error(data.error || 'The web search did not work.');
        const results = data.results || [];
        if (!results.length) { setStatus(`No new web listings with a confirmed source in ${data.area}. The blue pins are our reviewed listings.`); return; }
        setStatus(`Gemma found ${results.length} more on the web in ${data.area}. ${data.notice}`);
        window.clearHouseAssistantNote?.(`Update: I found ${results.length} more listing${results.length === 1 ? '' : 's'} on the web in ${data.area}. They're the orange pins on the map, not checked by our team yet.`);
        results.forEach(r => {
          const lines = [r.name, r.address, r.rent_text, r.income_text, 'Found on the web, not checked by our team'];
          if (typeof r.lat === 'number') addWebPin({ lat: r.lat, lon: r.lon, color: '#d9822b', title: r.name, popup: popup(lines, r.source_url, 'Source Page') });
          const li = el('li'); li.append(el('strong', r.name));
          [r.address, r.rent_text, r.income_text].filter(Boolean).forEach(t => li.append(el('div', t)));
          const link = safeUrl(r.source_url); if (link) li.append(el('a', 'Source Page', { href: link, target: '_blank', rel: 'noopener' }));
          webList.append(li);
        });
        webList.hidden = false;
      } catch (err) {
        if (id === searchId) setStatus(err.name === 'AbortError' ? 'The web search is taking too long. Our reviewed listings are still shown.' : (err.message || 'The web search did not work. Our reviewed listings are still shown.'));
      }
    }

    // Follow the area people pick in "Browse" and the place they type in "Where are you looking?".
    document.getElementById('browse-location')?.addEventListener('change', e => { selectArea(e.target.value); setStatus(e.target.value==='Blacksburg'?'Map centered on Blacksburg. Homes without confirmed coordinates remain in the list.':e.target.value ? `Showing ${e.target.value}.` : 'Pick or type an area to zoom in.'); });
    const typed = document.getElementById('location');
    // Searching the web uses Gemma with Google Search (only the Gemini API can do that, so it takes about a
    // minute). It's a button people choose, not something that runs every time the place changes.
    const webBtn = document.createElement('button');
    webBtn.type = 'button'; webBtn.className = 'web-search-btn'; webBtn.hidden = true;
    statusEl.after(webBtn);
    const offerWebSearch = place => { webBtn.textContent = `Search the web for more in ${place} (takes about a minute)`; webBtn.dataset.place = place; webBtn.hidden = false; };
    webBtn.addEventListener('click', () => { webBtn.hidden = true; liveSearch(webBtn.dataset.place); });
    typed?.addEventListener('change', () => {
      const text = typed.value.trim();
      if (!text || /^northern virginia$/i.test(text)) { selectArea(null); webBtn.hidden = true; setStatus('Pick or type an area to zoom in.'); return; }
      const area = areaFor(text) || (/blacksburg|virginia tech|christiansburg/i.test(text) ? 'Blacksburg' : null);
      const known = area || HOODS.nova.some(([n]) => n.toLowerCase().includes(text.toLowerCase())) || HOODS.blacksburg.some(([n]) => n.toLowerCase().includes(text.toLowerCase()));
      if (!known) { webBtn.hidden = true; setStatus('Clear House covers Northern Virginia and Blacksburg, VA. Try Blacksburg, Arlington, Reston, or Woodbridge.'); return; }
      window.clearHouseMapGoTo(text); offerWebSearch(text);
    });
  })();
