// Front page: hero, scenery, pinned scroll scenes, flip cards, map video, tonight chat.
// Used by the front page (/), frontend/about.html; runs where the page lists it.

// Debug only (add ?debug to the URL): cycle through font pairings to compare them.
if (new URLSearchParams(location.search).has('debug')) {
  const FONTS = [
    ['Inter', 'Inter', 'Inter'],
    ['Space Grotesk + Inter', 'Space Grotesk', 'Inter'],
    ['Poppins', 'Poppins', 'Poppins'],
    ['DM Sans', 'DM Sans', 'DM Sans'],
    ['Outfit', 'Outfit', 'Outfit'],
    ['Nunito', 'Nunito', 'Nunito'],
    ['Plus Jakarta Sans', 'Plus Jakarta Sans', 'Plus Jakarta Sans'],
    ['Fraunces + Inter', 'Fraunces', 'Inter'],
    ['Lora + Inter', 'Lora', 'Inter'],
    ['Pixelify Sans + Inter', 'Pixelify Sans', 'Inter'],
    ['Silkscreen + Inter', 'Silkscreen', 'Inter'],
    ['VT323 + Inter', 'VT323', 'Inter'],
  ];
  const families = [...new Set(FONTS.flatMap(f => [f[1], f[2]]))]
    .map(f => 'family=' + f.replace(/ /g, '+') + (['Silkscreen', 'VT323'].includes(f) ? '' : ':wght@400;600;700;800'))
    .join('&');
  const link = document.createElement('link');
  link.rel = 'stylesheet';
  link.href = 'https://fonts.googleapis.com/css2?' + families + '&display=swap';
  document.head.append(link);

  const switcher = document.querySelector('.font-switcher');
  const label = document.getElementById('font-name');
  let current = 0;
  const apply = () => {
    const [name, head, body] = FONTS[current];
    document.documentElement.style.setProperty('--font-head', `"${head}", sans-serif`);
    document.documentElement.style.setProperty('--font-body', `"${body}", sans-serif`);
    label.textContent = `${current + 1}/${FONTS.length}: ${name}`;
  };
  document.getElementById('font-next').addEventListener('click', () => { current = (current + 1) % FONTS.length;
    apply(); });
  document.getElementById('font-prev').addEventListener('click', () => { current = (current - 1 + FONTS.length) % FONTS.length;
    apply(); });
  switcher.hidden = false;
  apply();
}

// Scroll animations: reveal elements as they enter the screen.
const reveals = document.querySelectorAll('.reveal');
if (matchMedia('(prefers-reduced-motion: reduce)').matches || !('IntersectionObserver' in window)) {
  reveals.forEach(el => el.classList.add('visible'));
} else {
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      // In view: play the entrance. Out of view: reset, so it plays again when you scroll back up or down.
      entry.target.classList.toggle('visible', entry.isIntersecting);
    });
  }, { threshold: 0.12 });
  reveals.forEach(el => observer.observe(el));
  // A fast scroll can jump past an element without it ever being on screen,
  // so also reveal anything at or above the viewport.
  let pending = false;
  addEventListener('scroll', () => {
    if (pending) return;
    pending = true;
    requestAnimationFrame(() => {
      pending = false;
      document.querySelectorAll('.reveal:not(.visible)').forEach(el => {
        const r = el.getBoundingClientRect();
        if (r.top < innerHeight && r.bottom > 0) el.classList.add('visible'); // only what's on screen
      });
    });
  }, { passive: true });
}

// Built-with-Google flip cards: the back says how we use each service. Scrolling turns them over one by one, in order,
// and scrolling back up turns them back; a tap flips one by hand.
const flips = [...document.querySelectorAll('.flip')];
const setFlip = (card, on) => {
  const [front, back] = card.querySelectorAll('.face');
  card.classList.toggle('flipped', on);
  front.inert = on;
  back.inert = !on;
  front.querySelector('.flip-btn').setAttribute('aria-expanded', on);
};
flips.forEach(card => card.addEventListener('click', e => {
  const on = !card.classList.contains('flipped');
  setFlip(card, on);
  if (e.target.closest('.flip-btn')) card.querySelector(on ? '.back .flip-btn' : '.front .flip-btn').focus();
}));
// Scroll scenes. On wide screens a scene stays pinned on screen while the next `distance` px of scrolling play it, then
// the page carries on. So the page never looks frozen, everything in a scene moves with the scroll itself (nothing
// waits for a threshold), the stage drifts gently, and a progress bar at the bottom fills as you go. On phones a scene
// with a `deck` (a row of cards) pins too, showing one card at a time over `deckDistance` px; play() then gets `stops`,
// the slide that centers each card. Other narrow or short windows scroll freely and call loose() instead; reduced
// motion skips the scenes (callers show the finished state).
const calmPage = matchMedia('(prefers-reduced-motion: reduce)').matches,
  siteHeader = document.querySelector('.site-header');
const BIRD = '<svg viewBox="-10 -6 20 8.5"><g stroke="#7e9bc8" stroke-width="1.8" stroke-linecap="round" fill="none"><path class="wl" d="M0 0Q-4-5-9-3.5"/>' +
  '<path class="wr" d="M0 0Q4-5 9-3.5"/></g><ellipse cx=".6" cy=".4" rx="3.2" ry="1.5" fill="#7e9bc8"/><circle cx="3.4" cy="-.3" r="1.2" fill="#7e9bc8"/></svg>';
let scenes = 0;

function pinScene(track, { distance, play, loose, fitTo, deck, deckDistance }) {
  const stage = track.firstElementChild,
    fit = stage.firstElementChild;
  const bar = document.createElement('div');
  bar.className = 'scene-progress';
  bar.setAttribute('aria-hidden', 'true');
  bar.append('Keep scrolling', document.createElement('b'), document.createElement('i'));
  stage.append(bar);
  // A few birds cross the background: speed, start (as a share of the width, off to the left), height, size and
  // flap speed, varied per scene so no two look the same.
  const birds = document.createElement('div');
  birds.className = 'scene-birds';
  birds.setAttribute('aria-hidden', 'true');
  const turn = (scenes++ % 3) * .07;
  birds.innerHTML = [
      [1.5, -.3, 14, 1, 1.1],
      [1.8, -.62, 24, .75, .95],
      [1.3, -.2, 76, .9, 1.25],
      [1.65, -.48, 86, .65, 1]
    ]
    .map(([s, o, y, size, flap]) => `<i style="--s:${s + turn};--o:${o - turn};--y:${(y + turn * 60) % 92}%;--size:${size};--flap:${flap}s">${BIRD}</i>`).join('');
  stage.prepend(birds);
  let pinned = false,
    stops = null,
    laidOut = 0;
  const span = () => (stops && deckDistance) || distance;
  // Wide screens zoom the whole page (html zoom), so window sizes are divided by it to get CSS pixels.
  const zoom = () => parseFloat(getComputedStyle(document.documentElement).zoom) || 1;
  const layout = () => {
    track.classList.remove('pinned', 'deck');
    fit.style.zoom = fit.style.width = track.style.height = stage.style.paddingTop = '';
    deck?.style.removeProperty('--deck-x');
    fitTo?.(null);
    pinned = false;
    stops = null;
    laidOut = innerWidth;
    const phone = innerWidth < 900;
    if (phone && !deck) return;
    track.classList.add('pinned');
    if (phone) track.classList.add('deck');
    const top = siteHeader ? siteHeader.offsetHeight : 0,
      room = innerHeight / zoom() - top - (phone ? 66 : 44); // phones keep room for the bar at the bottom
    stage.style.paddingTop = `${top + 12}px`;
    bar.style.top = `${Math.max(8, (top - bar.offsetHeight) / 2)}px`; // in the header's row, at the very top of the window
    fit.style.width = `${stage.clientWidth}px`; // zoom then shrinks it evenly, keeping its columns
    if (fitTo) fitTo(room);
    const scale = Math.min(1, room / fit.offsetHeight);
    if (scale < (fitTo ? .98 : phone ? .72 : .6)) { track.classList.remove('pinned', 'deck');
      fit.style.width = stage.style.paddingTop = '';
      fitTo?.(null); return; }
    if (scale < 1 && !fitTo) fit.style.zoom = scale;
    if (phone) {
      // How far to slide the row (in its own pixels, whatever the zoom) to put each card in the middle of the screen.
      const row = deck.getBoundingClientRect(),
        s = row.width / deck.offsetWidth || 1;
      stops = [...deck.children].map(card => (innerWidth / 2 - row.left) / s - (card.offsetLeft - deck.offsetLeft + card.offsetWidth / 2));
    }
    track.style.height = `${innerHeight / zoom() + span()}px`;
    pinned = true;
  };
  // The scene glides after the scroll instead of following it 1:1, like skates on ice: each frame closes part of
  // the gap, so a notchy mouse wheel still turns into one smooth movement.
  let target = 0,
    shown = 0,
    last = 0,
    gliding = false;
  const draw = () => {
    stage.style.setProperty('--p', shown.toFixed(4));
    bar.classList.toggle('done', shown > .97);
    play(shown, stops);
  };
  const glide = now => {
    const dt = Math.min(64, now - (last || now - 16.7));
    last = now;
    shown += (target - shown) * (1 - Math.pow(1 - .12, dt / 16.7));
    if (Math.abs(target - shown) < .0005) shown = target;
    draw();
    if (shown !== target) requestAnimationFrame(glide);
    else { gliding = false;
      last = 0; }
  };
  const sync = (jump = false) => {
    if (!pinned) { loose?.(); return; }
    target = Math.min(1, Math.max(0, -track.getBoundingClientRect().top / (span() * zoom())));
    if (jump) { shown = target;
      draw(); return; } // on load and resize: no glide from wherever it was
    if (!gliding) { gliding = true;
      requestAnimationFrame(glide); }
  };
  const relayout = () => { layout();
    sync(true); };
  addEventListener('scroll', () => sync(), { passive: true });
  // On touch screens the address bar and keyboard change the height as you scroll; only a new width (turning the
  // phone) lays the scene out again, so the page doesn't jump.
  const touch = matchMedia('(pointer: coarse)').matches;
  addEventListener('resize', () => { if (!(touch && innerWidth === laidOut)) relayout(); });
  addEventListener('load', relayout);
  document.fonts?.ready.then(relayout);
  relayout();
  return () => pinned;
}
const ease = t => t * t * (3 - 2 * t);

// Flip cards. Pinned: each card turns with the scroll itself, in overlapping waves, so every bit of scrolling turns
// something; a tapped card keeps its side until the scroll carries it past halfway again. Narrow screens: each card
// turns over as it reaches the middle of the screen, and back when you scroll up past it.
const flipTrack = document.querySelector('.google-track');
if (flipTrack && !calmPage) {
  const LEAD = 30,
    TURN = 100,
    GAP = 40,
    TAIL = 90,
    distance = LEAD + GAP * (flips.length - 1) + TURN + TAIL;
  const grid = flipTrack.querySelector('.google-grid'),
    last = flips.length - 1,
    clamp01 = x => Math.min(1, Math.max(0, x));
  const turned = flips.map(() => false); // which side scrolling last asked for
  const byHand = new Map(); // card -> the side scrolling wanted when it was tapped
  const inner = card => card.querySelector('.flip-in');
  const show = (card, i, on) => { if (on !== card.classList.contains('flipped')) setFlip(card, on);
    turned[i] = on; };
  let isPinned = () => false;
  flips.forEach((card, i) => card.addEventListener('click', () => {
    if (!isPinned()) return;
    byHand.set(card, turned[i]);
    inner(card).style.transition = 'transform .6s cubic-bezier(.2,.7,.2,1)';
    inner(card).style.transform = `rotateY(${card.classList.contains('flipped') ? 180 : 0}deg)`;
  }));
  isPinned = pinScene(flipTrack, {
    distance,
    deck: grid,
    deckDistance: 230 * flips.length,
    play: (p, stops) => {
      let turn;
      if (stops) {
        // Phones: each card turns over in the middle of the screen, then the next one slides in.
        const u = Math.max(0, p * (last + .75) - .25),
          k = Math.min(last, Math.floor(u)),
          f = u - k;
        const x = k >= last ? stops[last] : stops[k] + (stops[k + 1] - stops[k]) * ease(clamp01((f - .45) / .55));
        grid.style.setProperty('--deck-x', `${x.toFixed(1)}px`);
        turn = i => clamp01((u - i) / .4);
      } else {
        const at = p * distance - LEAD;
        turn = i => clamp01((at - i * GAP) / TURN);
      }
      flips.forEach((card, i) => {
        const deg = 180 * ease(turn(i)),
          on = deg > 90;
        if (card.contains(document.activeElement)) return; // never turn the card a keyboard user is on
        if (byHand.has(card)) { if (byHand.get(card) === on) return;
          byHand.delete(card); }
        inner(card).style.transition = 'none';
        inner(card).style.transform = `rotateY(${deg.toFixed(1)}deg)`;
        if (on !== turned[i] || on !== card.classList.contains('flipped')) show(card, i, on);
      });
    },
    loose: () => flips.forEach((card, i) => {
      inner(card).style.transition = inner(card).style.transform = '';
      const r = card.getBoundingClientRect(),
        on = r.top + r.height / 2 < innerHeight * .55;
      if (on === turned[i] || card.contains(document.activeElement)) return;
      show(card, i, on);
    })
  });
}

// The map: a recording of someone using the live map (all of Northern Virginia, zooming into Ballston, near work in
// Reston, then Blacksburg, opening listings on the way). It plays on a slow, seamless loop while it's on screen,
// with a caption for each stop; with reduced motion it stays still, with play controls. The section isn't pinned.
// Stop times are from the recording (seconds).
const mapVideo = document.getElementById('map-video'),
  mapLead = document.querySelector('.map-track .cl-lead');
if (mapVideo && mapLead) {
  const STOPS = [
    [0, 'Every verified home across Northern Virginia.'],
    [8.8, 'Zoom into a neighborhood, like Ballston in Arlington.'],
    [24.9, 'Or look near work, like Reston.'],
    [36.0, 'And Blacksburg, right by Virginia Tech.']
  ];
  let stop = -1;
  mapVideo.addEventListener('timeupdate', () => {
    const i = STOPS.reduce((found, [from], n) => (mapVideo.currentTime >= from ? n : found), 0);
    if (i === stop) return;
    stop = i;
    mapLead.textContent = STOPS[i][1];
    mapLead.animate?.([{ opacity: 0, transform: 'translateY(6px)' }, { opacity: 1, transform: 'none' }], { duration: 260, easing: 'ease-out' });
  });
  if (calmPage) mapVideo.controls = true; // the browser's own controls, progress bar included
  else {
    mapVideo.loop = true;
    // Our controls over the video: pause/play, a progress bar (click to jump) and the time. Paused by the person, it
    // stays paused while scrolling.
    const bar = document.getElementById('map-player-bar'),
      toggle = bar.querySelector('button'),
      track = bar.querySelector('.map-player-track');
    const fill = bar.querySelector('.map-player-fill'),
      time = bar.querySelector('.map-player-time');
    const PAUSE = '<svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor" aria-hidden="true"><rect x="2.5" y="2" width="3.2" height="10" rx="1"/><rect x="8.3" y="2" width="3.2" height="10" rx="1"/></svg>';
    const PLAY = '<svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor" aria-hidden="true"><path d="M4 2.2v9.6a.6.6 0 0 0 .9.5l7.6-4.8a.6.6 0 0 0 0-1L4.9 1.7a.6.6 0 0 0-.9.5Z"/></svg>';
    const clock = t => `${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, '0')}`;
    let held = false;
    const draw = () => {
      const d = mapVideo.duration || 0,
        part = d ? mapVideo.currentTime / d : 0;
      fill.style.transform = `scaleX(${part})`;
      time.textContent = `${clock(mapVideo.currentTime)} / ${clock(d)}`;
      track.setAttribute('aria-valuenow', Math.round(part * 100));
    };
    const tick = () => { draw(); if (!mapVideo.paused) requestAnimationFrame(tick); };
    const icon = playing => { toggle.innerHTML = playing ? PAUSE : PLAY;
      toggle.setAttribute('aria-label', playing ? 'Pause the video' : 'Play the video'); };
    mapVideo.addEventListener('play', () => { icon(true);
      requestAnimationFrame(tick); });
    mapVideo.addEventListener('pause', () => { icon(false);
      draw(); });
    mapVideo.addEventListener('loadedmetadata', draw);
    mapVideo.addEventListener('seeked', draw);
    toggle.addEventListener('click', () => { held = !mapVideo.paused; if (held) mapVideo.pause();
      else mapVideo.play().catch(() => {}); });
    track.addEventListener('click', e => { const r = track.getBoundingClientRect(); if (mapVideo.duration) mapVideo.currentTime = Math.min(Math.max((e.clientX - r.left) / r.width, 0), .999) * mapVideo.duration;
      draw(); });
    icon(false);
    bar.hidden = false;
    // Load it as it nears the screen, play while it's mostly on screen, pause once it's scrolled away (checked on
    // scroll, so it doesn't depend on observers).
    const check = () => {
      const r = mapVideo.getBoundingClientRect(),
        seen = r.top < innerHeight * .8 && r.bottom > innerHeight * .2;
      if (r.top < innerHeight * 2 && r.bottom > -innerHeight) mapVideo.preload = 'auto';
      if (seen && mapVideo.paused && !held) mapVideo.play().catch(() => {});
      else if (!seen && !mapVideo.paused) mapVideo.pause();
    };
    addEventListener('scroll', check, { passive: true });
    addEventListener('resize', check);
    check();
  }
}

// How Clear Home Helps: a sample chat (each question appears, then Gemma types its answer) and the near-my-office
// search filling in. Pinned, the scroll itself types it, so scrolling back up rewinds; narrow screens play it once as
// it comes into view. The chat quotes real records from our verified list.
const howTrack = document.querySelector('.how-track');
if (howTrack) {
  const TALK = [{ me: 'I’m behind on rent in Arlington. Who can help?', at: .03 },
    { ai: [
        ['Call '],
        ['Arlington County DHS Emergency Financial Assistance', 1],
        [' at 703-228-1300. It helps Arlington tenants facing eviction with emergency rent.']
      ], at: .1, type: [.16, .42] },
    { me: 'And somewhere safe to sleep tonight?', at: .48 },
    { ai: [
        ['In danger, call 911. For a shelter bed, call '],
        ['Arlington DHS Shelter Access', 1],
        [' at 703-228-1300. Budget hotels nearby are listed too.']
      ], at: .54, type: [.6, .86] }
  ];
  const QUERY = 'Homes near my office in Reston',
    clamp = x => Math.min(1, Math.max(0, x));
  const chat = howTrack.querySelector('.cl-chat'),
    query = howTrack.querySelector('.cl-query'),
    homes = [...howTrack.querySelectorAll('.cl-list li')];
  const typed = (node, parts, n) => { // the first n characters show; the rest stay as invisible text holding the space
    node.replaceChildren();
    for (const [text, bold] of parts) {
      const part = document.createElement(bold ? 'b' : 'span'),
        shown = text.slice(0, Math.max(0, n)),
        ghost = document.createElement('span');
      ghost.className = 'ghost';
      ghost.textContent = text.slice(shown.length);
      part.append(shown, ghost);
      node.append(part);
      n -= text.length;
    }
  };
  const lines = TALK.map(line => {
    const bubble = document.createElement('span');
    bubble.className = (line.me ? 'me' : 'ai') + ' demo';
    if (line.me) bubble.textContent = line.me;
    else { bubble.total = line.ai.reduce((sum, [t]) => sum + t.length, 0);
      typed(bubble, line.ai, 0); }
    return bubble;
  });
  chat.replaceChildren(...lines);
  homes.forEach(li => li.classList.add('demo'));
  const chatAt = p => {
    TALK.forEach((line, i) => {
      const bubble = lines[i];
      bubble.classList.toggle('on', p >= line.at);
      if (!line.type) return;
      const n = Math.round(bubble.total * clamp((p - line.type[0]) / (line.type[1] - line.type[0])));
      bubble.classList.toggle('typing', p >= line.at && n === 0);
      if (bubble.shown === n) return;
      bubble.shown = n;
      typed(bubble, line.ai, n);
      const dots = document.createElement('span');
      dots.className = 'dots';
      dots.append(...[0, 1, 2].map(() => document.createElement('i')));
      bubble.append(dots);
    });
  };
  const searchAt = p => {
    typed(query, [
      [QUERY]
    ], Math.round(QUERY.length * clamp((p - .05) / .17)));
    homes.forEach((li, i) => li.classList.toggle('on', p >= .26 + i * .08));
  };
  const render = p => { chatAt(p);
    searchAt(p); };
  const duo = howTrack.querySelector('.cl-duo');
  if (calmPage) render(1);
  else {
    let played = false;
    const playOnce = () => { // the whole scene over 7 seconds, once it's in view
      if (played) return;
      const r = howTrack.getBoundingClientRect();
      if (r.top > innerHeight * .65 || r.bottom < 0) return;
      played = true;
      const t0 = performance.now(),
        tick = now => { const p = clamp((now - t0) / 7000);
          render(p); if (p < 1) requestAnimationFrame(tick); };
      requestAnimationFrame(tick);
    };
    render(0);
    pinScene(howTrack, {
      distance: 550,
      deck: duo,
      deckDistance: 1000,
      loose: playOnce,
      play: (p, stops) => {
        played = true;
        if (!stops) { render(p); return; }
        // Phones: the chat plays on the first card, the deck slides over, then the search fills in on the second.
        chatAt(clamp(p / .46));
        searchAt(clamp((p - .56) / .36) * .6);
        duo.style.setProperty('--deck-x', `${(stops[0] + (stops[1] - stops[0]) * ease(clamp((p - .46) / .12))).toFixed(1)}px`);
      }
    });
  }
}
