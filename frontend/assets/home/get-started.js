// 'Get started' intro: Gemma says hello, the first reply goes to /app.
// Used by the front page (/), frontend/about.html; runs where the page lists it.

// "Get started": open the intro, let Gemma say hello, and send the first reply to the tools page's chat.
(() => {
  const dlg = document.getElementById('start');
  if (!dlg || !dlg.showModal) return; // old browsers just follow the link
  const msgs = dlg.querySelector('.start-msgs'),
    input = document.getElementById('start-input');
  const calm = matchMedia('(prefers-reduced-motion: reduce)').matches;
  let greeted = false,
    leaving = false;
  // Off to the tools page (Skip or a first question): the card blurs away on the intro's dark blue, and the tools page
  // fades in from the same blue (its first-paint script reads the one-use 'ch:app-entry' marker).
  const openTools = () => {
    if (leaving) return; // one navigation, however many clicks
    leaving = true;
    dlg.classList.add('leaving');
    try { if (!calm) sessionStorage.setItem('ch:app-entry', String(Date.now())); } catch {}
    setTimeout(() => location.assign('/app'), calm ? 0 : 240);
  };
  dlg.querySelector('.start-skip').addEventListener('click', e => {
    if (e.button || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return; // a new tab or window gets the plain link
    e.preventDefault();
    openTools();
  });
  dlg.addEventListener('cancel', e => { if (leaving) e.preventDefault(); }); // Esc can't uncover this page mid-handoff
  // Back from the tools page out of the back/forward cache: the intro is closed and ready to open again.
  addEventListener('pageshow', e => { if (e.persisted && leaving) { leaving = false;
      dlg.classList.remove('leaving');
      dlg.close(); } });
  // iOS keeps the page full height when the keyboard opens, so size the intro to the visible part instead.
  const vv = window.visualViewport;
  const fit = () => { if (!vv) return;
    dlg.style.setProperty('--start-h', vv.height + 'px');
    dlg.style.setProperty('--start-top', vv.offsetTop + 'px'); };
  vv?.addEventListener('resize', fit);
  vv?.addEventListener('scroll', fit);
  document.querySelectorAll('a[data-start]').forEach(a => a.addEventListener('click', e => {
    if (e.button || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    e.preventDefault();
    dlg.classList.remove('leaving');
    dlg.showModal();
    fit();
    input.focus({ preventScroll: true });
    if (!greeted) {
      greeted = true;
      setTimeout(() => {
        const hello = document.createElement('p');
        hello.textContent = 'Hi, I’m Gemma. What kind of housing help do you need?';
        msgs.replaceChildren(hello);
      }, calm ? 0 : 900);
    }
  }));
  document.getElementById('start-form').addEventListener('submit', e => {
    e.preventDefault();
    const q = input.value.trim();
    if (!q) return;
    try { sessionStorage.setItem('ch:first-question', q); } catch {}
    openTools();
  });
})();

// "Need a place tonight?": a short guided chat in the same dark intro. Gemma checks the person is safe (911 first if
// not), then asks where: their location (only if they allow it) or an area. Then the tools page opens on shelters,
// intake lines and nearby budget hotels for that area. Scripted on purpose: in an emergency nothing waits on an AI.
(() => {
  const dlg = document.getElementById('tonight-chat');
  if (!dlg || !dlg.showModal) return; // old browsers just follow the link
  const msgs = dlg.querySelector('.start-msgs'),
    choices = document.getElementById('tonight-choices');
  const form = document.getElementById('tonight-form'),
    input = document.getElementById('tonight-input');
  const calm = matchMedia('(prefers-reduced-motion: reduce)').matches,
    wait = ms => new Promise(r => setTimeout(r, calm ? 0 : ms));
  let run = 0,
    leaving = false,
    onTyped = null;
  const scrollDown = () => { msgs.scrollTop = msgs.scrollHeight; };
  const say = (text, me) => { const p = document.createElement('p'); if (me) p.className = 'me';
    p.textContent = text;
    msgs.append(p);
    scrollDown(); };
  const gemma = async (text, ms = 700) => {
    const id = run,
      dots = document.createElement('p');
    dots.className = 'start-typing';
    dots.setAttribute('aria-label', 'Gemma is typing');
    dots.append(...[0, 1, 2].map(() => document.createElement('i')));
    msgs.append(dots);
    scrollDown();
    await wait(ms);
    dots.remove();
    if (id !== run) throw new Error('closed');
    say(text);
  };
  // Answer buttons (or links, like Call 911); the choice shows as the person's own reply.
  const ask = options => new Promise(resolve => {
    choices.replaceChildren(...options.map(o => {
      const b = document.createElement(o.href ? 'a' : 'button');
      b.className = 'start-choice' + (o.urgent ? ' urgent' : '');
      b.textContent = o.label;
      if (o.href) b.href = o.href;
      else b.type = 'button';
      b.addEventListener('click', () => { if (o.href) return;
        choices.replaceChildren();
        onTyped = null;
        say(o.label, true);
        resolve(o.value); });
      return b;
    }));
    choices.querySelector('button, a')?.focus({ preventScroll: true });
  });
  const typed = () => new Promise(resolve => { onTyped = resolve; });
  form.addEventListener('submit', e => {
    e.preventDefault();
    const place = input.value.trim();
    if (!place || !onTyped) return;
    const done = onTyped;
    onTyped = null;
    input.value = '';
    choices.replaceChildren();
    say(place, true);
    done(place);
  });
  const locate = () => new Promise(resolve => navigator.geolocation ?
    navigator.geolocation.getCurrentPosition(p => resolve(p.coords), () => resolve(null), { timeout: 12000, maximumAge: 600000 }) :
    resolve(null));
  // Which of our two areas a spot is in (rough miles from each center), or null outside both.
  const regionAt = (lat, lon) => {
    const miles = (a, b) => Math.hypot((lat - a) * 69, (lon - b) * 54);
    return miles(37.23, -80.42) < 30 ? 'Blacksburg' : miles(38.83, -77.3) < 40 ? 'Northern Virginia' : null;
  };
  const openTools = area => {
    if (leaving) return;
    leaving = true;
    try { if (area) sessionStorage.setItem('ch:tonight', area); if (!calm) sessionStorage.setItem('ch:app-entry', String(Date.now())); } catch {}
    dlg.classList.add('leaving');
    setTimeout(() => location.assign('/app#emergency'), calm ? 0 : 240);
  };
  async function chat() {
    const id = ++run;
    msgs.replaceChildren();
    choices.replaceChildren();
    form.hidden = true;
    onTyped = null;
    try {
      say('I need a place to stay tonight.', true);
      await gemma('I’m here to help. First, are you safe right now?', 900);
      const safe = await ask([{ label: 'I’m safe for now', value: true }, { label: 'I’m not safe', value: false, urgent: true }]);
      // Not safe: 911 first, and leaving abuse as its own answer there.
      const next = safe ? 'safe' : (await gemma('Please call 911 if you’re in danger right now. If it isn’t safe to talk, you can text 911 in many places. I’ll be right here.'),
        await ask([{ label: 'Call 911', href: 'tel:911', urgent: true }, { label: 'I’m leaving abuse', value: 'abuse' }, { label: 'I’m safe now', value: 'safe' }]));
      // Domestic violence shelters keep their addresses private, so the statewide hotline is the way in (checked 2026-10-25 on vsdvalliance.org).
      if (next === 'abuse') {
        await gemma('You deserve to be safe. The Virginia Family Violence & Sexual Assault Hotline is free, confidential and open 24/7. They can find you a domestic violence shelter (those keep their addresses private) and help you plan how to leave safely.');
        await ask([{ label: 'Call 1-800-838-8238', href: 'tel:+18008388238', urgent: true }, { label: 'Text 804-793-9999', href: 'sms:+18047939999' },
          { label: 'Show places to stay', value: true }
        ]);
      }
      await gemma('Where should I look? I can use your location to find the closest shelters and budget hotels, or you can pick an area.');
      let area = null;
      while (!area) {
        form.hidden = false;
        const pick = await Promise.race([ask([{ label: 'Use my location', value: 'here' }, { label: 'Northern Virginia', value: 'Northern Virginia' },
          { label: 'Blacksburg', value: 'Blacksburg' }
        ]), typed()]);
        form.hidden = true;
        if (pick !== 'here') { area = pick; break; }
        await gemma('Your browser will ask to share your location. It stays on this device; I only use it to pick the area.', 500);
        const spot = await locate();
        area = spot && regionAt(spot.latitude, spot.longitude);
        if (!area) await gemma(spot ? 'You look to be outside Northern Virginia and Blacksburg, where Clear Home works. Call 211: they help anywhere in Virginia. Or pick one of our areas.' :
          'I couldn’t get your location, and that’s okay. Pick an area or type a city.');
      }
      await gemma(`Okay. Opening shelters, intake lines and nearby budget hotels for ${area}. You can call 211 any time for help getting a bed.`);
      await wait(1200);
      if (id === run) openTools(area);
    } catch {} // closed partway: the next open starts over
  }
  // iOS keeps the page full height when the keyboard opens, so size the chat to the visible part instead.
  const vv = window.visualViewport;
  const fit = () => { if (!vv) return;
    dlg.style.setProperty('--start-h', vv.height + 'px');
    dlg.style.setProperty('--start-top', vv.offsetTop + 'px'); };
  vv?.addEventListener('resize', fit);
  vv?.addEventListener('scroll', fit);
  document.querySelectorAll('a[data-tonight-start]').forEach(a => a.addEventListener('click', e => {
    if (e.button || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return; // a new tab or window gets the plain link
    e.preventDefault();
    leaving = false;
    dlg.classList.remove('leaving');
    dlg.showModal();
    fit();
    chat();
  }));
  let fromTools = false;
  const skip = dlg.querySelector('.start-skip');
  skip.addEventListener('click', e => {
    if (e.button || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    e.preventDefault();
    // The X goes back to the tools page as it was left; without that page in the history, it opens the tools page.
    if (fromTools && !leaving && history.length > 1 && document.referrer.startsWith(location.origin + '/app')) {
      leaving = true;
      dlg.classList.add('leaving');
      setTimeout(() => history.back(), calm ? 0 : 240);
      return;
    }
    openTools(null);
  });
  // From the tools page's "I need a place tonight" (/?tonight): open this chat straight away, as if it had been started
  // here, with an X to go back instead of Skip, and drop the marker from the address so a reload doesn't reopen it.
  if (new URLSearchParams(location.search).has('tonight')) {
    history.replaceState(null, '', location.pathname + location.hash);
    fromTools = true;
    skip.classList.add('start-x');
    skip.setAttribute('aria-label', 'Close and go back to the tools page');
    skip.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18"/></svg>';
    leaving = false;
    dlg.showModal();
    fit();
    chat();
  }
  dlg.addEventListener('close', () => { run++; }); // closing stops the script
  dlg.addEventListener('cancel', e => { if (leaving) e.preventDefault(); });
  addEventListener('pageshow', e => { if (e.persisted && leaving) { leaving = false;
      dlg.classList.remove('leaving');
      dlg.close(); } });
})();
