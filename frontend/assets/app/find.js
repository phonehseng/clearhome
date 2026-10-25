// Find form and the Ask Gemma chat.
// Used by the tools page (/app), frontend/index.html; runs where the page lists it.

// Find form: instant options from the reviewed catalog, then an optional chat with the assistant.
(() => {
  const form = document.getElementById('find-form');
  const results = document.getElementById('find-results');
  const assistant = document.getElementById('assistant');
  const log = document.getElementById('assistant-log');
  const chatForm = document.getElementById('assistant-form');
  const chatInput = document.getElementById('assistant-input');
  const el = (tag, text, attrs = {}) => { const n = document.createElement(tag); if (text != null) n.textContent = text; for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v); return n; };
  const safeUrl = u => typeof u === 'string' && u.startsWith('https://') ? u : null;
  const tel = p => ClearHomeDial(p);
  const STATUS = { available_now: 'Available now', advertised_vacancy: 'Vacancy advertised', upcoming: 'Coming soon', leasing: 'Now leasing', waitlist_open: 'Waitlist open', contact_for_availability: 'Call for availability' };
  let profile = {},
    history = [];

  // "I need a place tonight" example also ticks the tonight box.
  document.querySelectorAll('[data-example]').forEach(b => b.addEventListener('click', () => { document.getElementById('more-options').open = true; if (/tonight/i.test(b.textContent)) document.getElementById('tonight').checked = true; }));

  // Links say where they go: a program page, an official county listing, or the provider's website.
  function resourceLinks(r) {
    if (Array.isArray(r.links) && r.links.length) return r.links.filter(l => safeUrl(l.url)).map(l => ({ url: l.url, label: l.label, note: l.note }));
    const out = [],
      seen = new Set(),
      add = (url, label) => { if (safeUrl(url) && !seen.has(url)) { seen.add(url);
          out.push({ url, label }); } };
    const sourceLabel = r.source_kind === 'official_directory' || /fairfaxcounty\.gov\/homeless\/emergency-shelters|directory|guide/i.test(r.source_url || '') ? 'Official county listing' : 'Program details';
    add(r.website, 'Provider website');
    add(r.source_url, sourceLabel);
    return out;
  }

  function shelterCard(r) {
    const c = el('article', null, { class: 'opt-card shelter' });
    c.append(stockBanner(r.type === 'emergency_shelter' ? 'shelter' : r.type, `${r.jurisdiction || ''} ${r.city || ''}`));
    // Never a promise of a bed: what the source supports, or "call to confirm".
    const badge = r.intake_status === 'closed' ? (r.intake_status_note || 'Closed right now') : r.referral_required ? 'Referral or screening required' : 'Call to confirm a bed tonight';
    c.append(el('span', badge, { class: 'opt-badge confirm' }));
    c.append(el('strong', r.name));
    const meta = [r.city || r.jurisdiction, r.distance_from_blacksburg].filter(Boolean).join(' · ');
    if (meta) c.append(el('span', meta, { class: 'meta' }));
    if (r.who_it_serves) c.append(el('span', r.who_it_serves.slice(0, 200), { class: 'meta' }));
    if (r.phone) {
      const call = el('div', null, { class: 'shelter-call' });
      call.append(el('a', `Call ${r.phone}`, { href: tel(r.phone) }));
      const role = { 'direct shelter line': 'Shelter’s own line', 'coordinated entry / referral line': 'Intake and referral line: they screen and refer you to a shelter' } [r.phone_role];
      if (role) call.append(el('small', role));
      c.append(call);
    }
    const steps = r.intake_steps || r.how_to_apply;
    if (steps || r.intake_hours || r.after_hours || r.requirements) {
      const d = el('details');
      d.append(el('summary', 'How to Get In'));
      if (steps) d.append(el('p', steps));
      if (r.intake_hours) d.append(el('p', 'Intake hours: ' + r.intake_hours));
      if (r.requirements) d.append(el('p', 'Who it’s for: ' + r.requirements));
      if (r.after_hours) d.append(el('p', 'If intake is closed or full: ' + r.after_hours));
      c.append(d);
    }
    // Where to go: only a public intake entrance gets directions; offices and confidential sites don't.
    const addr = r.public_intake_address || (r.address_kind === 'public intake entrance' ? r.address : null);
    if (r.confidential_location) c.append(el('span', 'The location is kept private for safety. Call to arrange intake.', { class: 'shelter-where' }));
    else if (addr) {
      const where = el('span', 'Go to: ' + addr + ' ', { class: 'shelter-where' });
      where.append(el('a', 'Get Directions ↗', { href: 'https://www.google.com/maps/dir/?api=1&destination=' + encodeURIComponent(addr), target: '_blank', rel: 'noopener' }));
      c.append(where);
    } else if (r.address && r.address_kind === 'office, not a walk-in shelter') c.append(el('span', 'Office address (not a walk-in shelter): ' + r.address, { class: 'shelter-where' }));
    if (r.transit) c.append(el('span', 'Getting there: ' + r.transit, { class: 'shelter-where' }));
    const links = el('div', null, { class: 'opt-links' });
    resourceLinks(r).forEach(l => { const a = el('a', l.label + ' ↗', { href: l.url, target: '_blank', rel: 'noopener' }); if (l.note) a.title = l.note;
      links.append(a); });
    if (links.childNodes.length) c.append(links);
    const notes = resourceLinks(r).filter(l => l.note).map(l => l.note);
    if (notes.length) c.append(el('span', notes.join(' '), { class: 'shelter-where' }));
    return c;
  }

  function card(r, kind) {
    if (kind === 'shelter') return shelterCard(r);
    const c = el('article', null, { class: 'opt-card' });
    c.append(stockBanner(kind === 'listing' ? 'listing' : r.type, `${r.jurisdiction || ''} ${r.city || ''}`));
    if (kind === 'listing' && STATUS[r.availability_status]) c.append(el('span', STATUS[r.availability_status], { class: 'opt-badge' }));
    if (kind === 'program' && r.waitlist_status === 'closed') c.append(el('span', 'Waitlist closed', { class: 'opt-badge closed' }));
    if (kind === 'program' && r.waitlist_status === 'open') c.append(el('span', 'Waitlist open', { class: 'opt-badge' }));
    c.append(el('strong', r.community || r.name));
    const meta = [r.floor_plan, r.jurisdiction, typeof r.monthly_rent === 'number' ? ClearHomeRental.price(r) : null].filter(Boolean).join(' · ');
    if (meta) c.append(el('span', meta, { class: 'meta' }));
    if (ClearHomeRental.term(r)) c.append(el('span', ClearHomeRental.term(r), { class: 'meta' }));
    if (ClearHomeRental.lease(r)) c.append(el('span', ClearHomeRental.lease(r), { class: 'meta' }));
    if (kind !== 'listing' && r.who_it_serves) c.append(el('span', r.who_it_serves.slice(0, 160), { class: 'meta' }));
    const links = el('div', null, { class: 'opt-links' });
    if (r.phone) links.append(el('a', r.phone, { href: tel(r.phone) }));
    resourceLinks(r).slice(0, 2).forEach(l => links.append(el('a', l.label, { href: l.url, target: '_blank', rel: 'noopener' })));
    c.append(links);
    return c;
  }

  function group(title, rows, kind, empty) {
    const box = el('section');
    box.append(el('h4', title));
    if (!rows.length) { box.append(el('p', empty, { class: 'opt-empty' })); return box; }
    const grid = el('div', null, { class: 'opt-grid' });
    rows.forEach(r => grid.append(card(r, kind)));
    box.append(grid);
    return box;
  }
  // Somewhere to stay tonight besides a shelter: budget hotels and motels near the area from Google Maps.
  // Our team hasn't verified them, so they say so, and a Google Maps link shows more.
  const HOTEL_NOTE = 'Not verified by our team, and prices are estimates: call to ask tonight’s rate and whether a room is free. If the cost is a problem, ask 211 whether help paying for a room is available.';
  const hotelsShown = new Set(); // places whose hotels are already on screen, so the chat doesn't list them twice
  const panelHotels = new Set(); // the ones the options panel lists (forgotten when it's closed)
  const hotelsOnPanel = place => { hotelsShown.add(place);
    panelHotels.add(place); };
  const hotelSearch = place => 'https://www.google.com/maps/search/?api=1&query=' + encodeURIComponent('hotels near ' + place);
  const hotelMeta = h => [h.kind, typeof h.rating === 'number' ? `★ ${h.rating.toFixed(1)}${h.ratings ? ` (${h.ratings.toLocaleString('en-US')})` : ''}` : null].filter(Boolean).join(' · ');
  // An estimate, never a quote: the nightly range, then a line saying what it rests on (Google's price level, the chain, or neither).
  function hotelCost(h, metaClass) {
    const e = h.estimate;
    if (!e || typeof e.low !== 'number' || typeof e.high !== 'number') return [];
    const cost = el('span', null, { class: `${metaClass} hotel-cost` });
    cost.append(el('b', `Est. $${e.low}–$${e.high} / night`), ' · call for tonight’s rate');
    return e.basis ? [cost, el('span', e.basis, { class: `${metaClass} hotel-basis` })] : [cost];
  }
  const hotelMore = url => el('a', 'See More Hotels on Google Maps ↗', { href: url, target: '_blank', rel: 'noopener', class: 'hotel-more' });
  async function fetchHotels(place) {
    const res = await fetch('/api/hotels', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ place }) });
    const data = await res.json();
    if (!res.ok || data.error) throw new Error(data.error || 'Hotels could not be loaded.');
    return data;
  }

  function hotelCard(h) {
    const c = el('article', null, { class: 'opt-card' });
    c.append(stockBanner('hotel'));
    c.append(el('span', 'Google Maps · not verified by us', { class: 'opt-badge web' }), el('strong', h.name));
    if (hotelMeta(h)) c.append(el('span', hotelMeta(h), { class: 'meta' }));
    c.append(...hotelCost(h, 'meta'));
    if (h.address) c.append(el('span', h.address, { class: 'meta' }));
    const links = el('div', null, { class: 'opt-links' });
    if (h.phone) links.append(el('a', `Call ${h.phone}`, { href: tel(h.phone) }));
    const site = safeUrl(h.website);
    if (site) links.append(el('a', 'Website ↗', { href: site, target: '_blank', rel: 'noopener' }));
    const map = safeUrl(h.maps_url);
    if (map) links.append(el('a', 'Google Maps ↗', { href: map, target: '_blank', rel: 'noopener' }));
    c.append(links);
    return c;
  }

  function hotelGroup(place) {
    const box = el('section');
    const note = el('p', 'Looking up hotels and motels on Google Maps…', { class: 'opt-empty' });
    box.append(el('h4', 'Hotels & Motels'), note);
    hotelsOnPanel(place.toLowerCase());
    fetchHotels(place).then(data => {
      hotelsOnPanel(data.place.toLowerCase());
      if (!data.hotels.length) { note.textContent = 'We couldn’t list hotels here right now. Google Maps can show what’s nearby.';
        box.append(hotelMore(safeUrl(data.search_url) || hotelSearch(place))); return; }
      note.textContent = `Budget hotels and motels from Google Maps. ${HOTEL_NOTE}`;
      note.className = 'hotel-note';
      const grid = el('div', null, { class: 'opt-grid' });
      data.hotels.forEach(h => grid.append(hotelCard(h)));
      box.append(grid, hotelMore(safeUrl(data.search_url) || hotelSearch(place)));
    }).catch(() => { note.textContent = 'Hotels couldn’t be loaded right now. Google Maps can show what’s nearby.';
      box.append(hotelMore(hotelSearch(place))); });
    return box;
  }
  // Plain text with **bold** names; built from text nodes, so nothing from the server runs as HTML.
  // Gemma sometimes answers in markdown; turn tables, headings and list marks into clean lines of text.
  function tidy(text) {
    return text.split('\n').map(line => {
      // Markdown escapes (\* \_ \#) show as the plain character; a line wrapped in *italics* (Gemma's footnotes) loses the stars.
      line = line.replace(/\\\*/g, '✱').replace(/\\([_#|`\-])/g, '$1');
      line = line.replace(/\$\\(?:le|leq)\$/g, '≤').replace(/\$\\(?:ge|geq)\$/g, '≥').replace(/\$\\(?:times)\$/g, '×').replace(/\$\\approx\$/g, '≈'); // math marks as plain symbols
      if (/^\s*\*[^*\s](.*[^*\s])?\*\s*$/.test(line)) line = line.trim().slice(1, -1);
      line = line.replace(/✱/g, '*');
      const t = line.trim();
      if (/^\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?$/.test(t) || /^-{3,}$|^\*{3,}$/.test(t)) return null; // table rules, dividers
      if (/^\|.*\|$/.test(t)) return '• ' + t.slice(1, -1).split('|').map(c => c.trim()).filter(Boolean).join(' · '); // table row
      if (/^#{1,6}\s+/.test(t)) return t.replace(/^#{1,6}\s+/, ''); // heading
      if (/^[*-]\s+/.test(t)) return '• ' + t.replace(/^[*-]\s+/, ''); // bullet
      return line;
    }).filter(l => l !== null).join('\n').replace(/^(based on the (data|information|resources) provided,?\s*)/i, '').replace(/\n{3,}/g, '\n\n').replace(/^\s*[a-z]/, c => c.toUpperCase());
  }

  function setText(m, text) {
    m.replaceChildren();
    text = tidy(text);
    text.split(/(\*\*[^*]+\*\*)/).forEach(part => m.append(part.startsWith('**') && part.endsWith('**') ? el('strong', part.slice(2, -2)) : document.createTextNode(part)));
  }

  function botSay(text, state) {
    const m = el('div', null, { class: 'msg bot' });
    if (state) m.dataset.state = state;
    setText(m, text);
    log.append(m);
    pinTurn();
    return m;
  }
  // A new question goes to the top of the chat box and its answer fills in below it, like a fresh page.
  // Space under the answer is padded so the question can sit at the top even while the answer is short.
  let turnStart = null;

  function pinTurn(scroll) {
    if (!turnStart) { log.scrollTop = log.scrollHeight; return; }
    const top = turnStart.offsetTop - 12; // the log is position:relative, so offsetTop is measured inside it
    const last = log.lastElementChild;
    const below = last.offsetTop + last.offsetHeight - turnStart.offsetTop; // this turn's content so far
    log.style.paddingBottom = `${Math.max(16, log.clientHeight - below - 12)}px`;
    if (scroll) log.scrollTop = top;
  }

  function userSay(text) { log.classList.add('chatting');
    turnStart = el('div', text, { class: 'msg user' });
    log.append(turnStart);
    pinTurn(true); }

  // Gemma's follow-up questions: when a request is missing something that changes the answer (which area, what kind of
  // help), the reply is one question with answer buttons. The server sends it as data (never HTML) plus this
  // conversation's answers ("state"), which go back with each message; the server checks every value.
  let chat = {},
    busy = false,
    chatReset = 0,
    inflight = null; // chatReset counts resets, so a reply still on its way can't bring old answers back
  // Starting over (the find form's results): cancel the reply on its way and free the composer at once.
  const cancelChat = () => { chatReset++;
    inflight?.abort();
    inflight = null;
    busy = false;
    chatForm.querySelector('button').disabled = false; };
  const PLACEHOLDER = chatInput.placeholder,
    ANSWER_HINT = 'Or type your own answer';

  function closeQuestions() { // a new message closes any open question, so a late click can't answer a stale one
    const open = [...log.querySelectorAll('fieldset.chat-q:not(:disabled)')];
    open.forEach(box => { box.disabled = true;
      box.dataset.state = 'closed'; });
    return open;
  }

  function showQuestion(bubble, q, focus, words) {
    const choices = Array.isArray(q?.choices) ? q.choices.filter(c => typeof c?.id === 'string' && typeof c?.label === 'string' && c.label.trim()).slice(0, 8) : [];
    if (typeof q?.id !== 'string' || (!choices.length && !q.skip && !q.unsure)) return; // malformed: the words still show, and typing still works
    const box = el('fieldset', null, { class: 'chat-q' });
    box.dataset.qid = q.id;
    // The question itself labels its buttons, so it moves out of the bubble's text into the group's legend.
    const text = typeof q.text === 'string' && q.text.trim() ? q.text.trim() : 'Choose an answer';
    if (words.trim().endsWith(text)) { setText(bubble, words.trim().slice(0, -text.length).trim());
      box.append(el('legend', text)); } else box.append(el('legend', text, { class: 'visually-hidden' }));
    const row = el('div', null, { class: 'chat-q-choices' }),
      more = el('div', null, { class: 'chat-q-more' });
    const send = async (ids, label, e) => {
      if (busy || box.disabled) return;
      box.disabled = true;
      box.dataset.state = 'answered'; // the buttons fold away; the pick shows as the person's reply
      // Keyboard users (a click with no pointer) keep their place: focus moves on to what comes next.
      if (!(await ask(label, { id: q.id, choices: ids }, e.detail === 0))) { box.disabled = false;
        delete box.dataset.state;
        chatInput.placeholder = ANSWER_HINT; }
    };
    const escape = (id, label) => { const b = el('button', label, { type: 'button', class: 'chat-q-choice escape' });
      b.addEventListener('click', e => send([id], label, e));
      more.append(b); };
    if (q.multi) { // several can apply: tick them, then Continue
      choices.forEach(c => { const tick = el('label', null, { class: 'chat-q-check' });
        tick.append(el('input', null, { type: 'checkbox', value: c.id }), document.createTextNode(c.label));
        row.append(tick); });
      const go = el('button', 'Continue', { type: 'button', class: 'chat-q-continue' });
      go.disabled = true;
      row.addEventListener('change', () => { go.disabled = !row.querySelector('input:checked'); });
      go.addEventListener('click', e => { const picked = [...row.querySelectorAll('input:checked')];
        send(picked.map(i => i.value), picked.map(i => i.parentElement.textContent).join(', '), e); });
      more.append(go);
    } else choices.forEach(c => { const b = el('button', c.label, { type: 'button', class: 'chat-q-choice' });
      b.addEventListener('click', e => send([c.id], c.label, e));
      row.append(b); });
    if (q.unsure) escape('unsure', 'Not sure');
    if (q.skip) escape('skip', 'Skip');
    if (q.custom !== false) { const type = el('button', 'Type My Own Answer', { type: 'button', class: 'chat-q-type' });
      type.addEventListener('click', () => chatInput.focus());
      more.append(type); }
    box.append(row, more);
    bubble.append(box);
    chatInput.placeholder = ANSWER_HINT;
    if (focus) box.querySelector('button:not(:disabled), input')?.focus({ preventScroll: true });
    pinTurn();
  }

  // Streams the answer: a progress note right away, then Gemma's words as they're written.
  // reply: a button answer to the open question; returns whether an answer came back (so a failed click can be retried).
  async function ask(question, reply, keyboard) {
    if (busy) return false;
    busy = true;
    const resets = chatReset,
      closed = closeQuestions();
    chatInput.placeholder = PLACEHOLDER;
    log.querySelectorAll('.chat-next').forEach(n => n.remove()); // the last answer's "more" buttons
    userSay(question);
    const button = chatForm.querySelector('button');
    button.disabled = true;
    const started = Date.now();
    const status = botSay('Reading your question…', 'loading');
    let note = 'Reading your question…';
    const timer = setInterval(() => { status.textContent = `${note} (${Math.round((Date.now() - started) / 1000)}s)`; }, 1000);
    let answer = '',
      bubble = null,
      engine = '',
      asked = null,
      state = null,
      lines = null,
      more = [],
      suggest = [],
      advice = false,
      ok = false;
    const show = text => { if (!bubble) { bubble = botSay(''); } setText(bubble, text);
      pinTurn(); };
    const finish = () => { clearInterval(timer);
      status.remove(); };
    const stale = () => resets !== chatReset; // the chat was reset while this reply was on its way
    const controller = new AbortController();
    inflight = controller;
    try {
      const stop = setTimeout(() => controller.abort(), 180000); // a careful think on specific needs can take two minutes
      const res = await fetch('/api/ask/stream', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question, history, profile: { ...profile, ...oneShot }, chat, ...(reply ? { reply } : {}) }), signal: controller.signal });
      oneShot = {};
      if (!res.ok || !res.body) { const data = await res.json().catch(() => ({})); throw new Error(data.error || 'Something went wrong.'); }
      const reader = res.body.getReader(),
        decoder = new TextDecoder();
      let buffer = '';
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let cut;
        while ((cut = buffer.indexOf('\n\n')) >= 0) {
          const line = buffer.slice(0, cut).replace(/^data: /, '');
          buffer = buffer.slice(cut + 2);
          let event;
          try { event = JSON.parse(line); } catch { continue; }
          if (stale()) throw new DOMException('reset', 'AbortError');
          if (event.kind === 'engine') { engine = event.text; } else if (event.kind === 'state') { if (event.text && typeof event.text === 'object') state = event.text; } else if (event.kind === 'question') { asked = event.text; } else if (event.kind === 'lines') { if (Array.isArray(event.text)) lines = event.text; } else if (event.kind === 'more') { if (Array.isArray(event.text)) more = event.text; } else if (event.kind === 'advice') { advice = event.text === true; } else if (event.kind === 'suggest') { if (Array.isArray(event.text)) suggest = event.text.filter(t => typeof t === 'string' && t.length < 120).slice(0, 3); } else if (event.kind === 'status') { note = event.text;
            status.textContent = note; } else if (event.kind === 'thinking') { note = `Gemma is thinking: ${event.text}`;
            status.textContent = note; } else if (event.kind === 'chunk') { if (!answer) finish();
            answer += event.text;
            show(answer); } else if (event.kind === 'cards') { if (bubble && Array.isArray(event.text) && event.text.length) showCards(bubble, answer, event.text, advice ? 0 : SHOWN); } else if (event.kind === 'hotels') { if (bubble && Array.isArray(event.text?.hotels)) showHotels(bubble, event.text); } else if (event.kind === 'answer' || event.kind === 'fallback') { finish();
            answer = event.text;
            show(answer); if (event.kind === 'fallback') bubble.dataset.state = 'notice'; }
        }
      }
      clearTimeout(stop);
      finish();
      if (stale()) throw new DOMException('reset', 'AbortError');
      if (!answer) throw new Error('No answer came back.');
      if (lines) showLines(bubble, lines);
      if (asked) showQuestion(bubble, asked, keyboard, answer);
      else if (keyboard) chatInput.focus({ preventScroll: true });
      if (engine) { const by = el('div', (asked ? 'Asked by ' : 'Answered by ') + engine, { class: 'msg-engine' }); let after = bubble; while (/\bchat-(cards|lines)\b/.test(after.nextElementSibling?.className || '')) after = after.nextElementSibling;
        after.after(by);
        pinTurn(); }
      if (!asked) showNext(more, /Gemma 4 26B/.test(engine) && !lines, suggest, bubble); // short answers: more on request; no match: next searches
      history.push({ role: 'user', text: question }, { role: 'assistant', text: answer });
      if (state && resets === chatReset) chat = state; // only once the whole reply arrived, so a failed one leaves the open question open
      ok = true;
    } catch (err) {
      finish();
      if (stale()) return false; // reset meanwhile: an old reply or error never shows in the new chat, and cancelChat freed the composer
      const msg = err.name === 'AbortError' ? 'This is taking too long, the AI service is busy. Please try again in a minute.' : err instanceof TypeError ? 'We could not reach the assistant. Check your connection and try again.' : (err.message || 'We could not reach the assistant.');
      botSay(/211/.test(msg) ? msg : msg + ' For urgent help, call 211.', 'error'); // the server's message may already say 211
      if (!reply) closed.forEach(box => { if (box.dataset.qid === chat.pending?.id) { box.disabled = false;
          delete box.dataset.state;
          chatInput.placeholder = ANSWER_HINT; } }); // still the open question: answer it again
    }
    if (inflight === controller) inflight = null;
    button.disabled = false;
    busy = false;
    return ok;
  }
  // An answer shows two places. "Show N more options" expands the message where it is: the rest of its list, the rest of
  // its cards, then the other places Gemma weighed (from the verified list, no AI call). "Tell me more" asks Gemma to
  // go into detail.
  function showNext(more, tellMore, suggest = [], bubble = null) {
    const row = el('div', null, { class: 'chat-next', role: 'group', 'aria-label': 'More from this answer' });
    const box = bubble?.nextElementSibling?.classList.contains('chat-cards') ? bubble.nextElementSibling : null;
    const lines = bubble ? [...bubble.querySelectorAll('.chat-extra[hidden]')] : [],
      cards = box ? [...box.querySelectorAll('.chat-card[hidden]')] : [];
    const count = Math.max(lines.length, cards.length) + more.length,
      none = box ? !box.querySelector('.chat-card:not([hidden])') : true;
    if (count) {
      // Advice answers show no cards at first: the button offers the places that can help.
      const b = el('button', none ? `Show ${count} place${count === 1 ? '' : 's'} that can help` : `Show ${count} more option${count === 1 ? '' : 's'}`, { type: 'button' });
      b.addEventListener('click', () => {
        lines.forEach(n => { n.hidden = false; });
        cards.forEach(n => { n.hidden = false; });
        let list = box;
        if (!list && more.length) { list = el('div', null, { class: 'chat-cards', role: 'list', 'aria-label': 'More options' });
          bubble.after(list); }
        more.forEach(c => list.append(chatCard(c)));
        b.remove();
        if (!row.children.length) row.remove();
        const all = [...(box?.cardsData || []), ...more];
        if (all.length) window.clearHomeMapFocus?.(all, `Map shows the ${all.length} places in this answer.`);
        (cards[0] || list?.children[list.children.length - more.length])?.focus({ preventScroll: true }); // keyboard: on to the first new card
        pinTurn();
      });
      row.append(b);
    }
    // Next searches when nothing matched (each one changes one thing); a tap asks it like a typed message.
    suggest.forEach(text => { const b = el('button', text, { type: 'button' });
      b.addEventListener('click', () => ask(text));
      row.append(b); });
    if (tellMore) {
      const b = el('button', 'Tell me more', { type: 'button' });
      b.addEventListener('click', () => ask('Tell me more about these, like how to apply and what to ask them.'));
      row.append(b);
    }
    if (row.children.length) { log.append(row);
      pinTurn(); }
  }
  // Crisis answers (suicide, self-harm, abuse at home) come with call and text buttons for the hotlines: one tap on a phone.
  function showLines(bubble, lines) {
    const row = el('div', null, { class: 'chat-lines', role: 'group', 'aria-label': 'Call or text for help' });
    lines.filter(l => typeof l?.href === 'string' && /^(tel|sms):\+?\d{3,11}$/.test(l.href) && typeof l.label === 'string')
      .forEach(l => row.append(el('a', l.label, { href: l.href, class: l.href === 'tel:911' ? 'urgent' : '' })));
    if (row.children.length) { bubble.after(row);
      pinTurn(); }
  }
  // Hotels and motels for a "somewhere to stay tonight" question, under the answer and its cards.
  function showHotels(bubble, data) {
    const place = data.place.toLowerCase();
    if (hotelsShown.has(place) || hotelsShown.has(place.replace(/, va$/, ''))) return; // already listed with the form's options
    hotelsShown.add(place);
    const box = el('div', null, { class: 'chat-hotels' });
    box.append(el('p', data.hotels.length ? `Budget hotels and motels near ${data.place}, from Google Maps. ${HOTEL_NOTE}` : `Need a hotel instead? Google Maps shows what’s near ${data.place}.`, { class: 'hotel-note' }));
    if (data.hotels.length) {
      const list = el('div', null, { class: 'chat-cards', role: 'list', 'aria-label': `Hotels and motels near ${data.place}` });
      data.hotels.slice(0, 4).forEach(h => {
        const card = el('article', null, { class: 'chat-card', role: 'listitem', 'aria-label': h.name });
        const media = el('div', null, { class: 'chat-card-media stock-thumb', 'aria-hidden': 'true' });
        media.style.setProperty('--thumb', 'url("/images/stock-hotel.jpg")');
        const body = el('div', null, { class: 'chat-card-body' });
        body.append(el('span', 'Google Maps · not verified by us', { class: 'opt-badge web' }), el('span', h.name, { class: 'chat-card-title' }));
        if (hotelMeta(h)) body.append(el('span', hotelMeta(h), { class: 'chat-card-meta' }));
        body.append(...hotelCost(h, 'chat-card-meta'));
        if (h.address) body.append(el('span', h.address, { class: 'chat-card-address' }));
        const links = el('div', null, { class: 'chat-card-actions' });
        if (h.phone) links.append(el('a', h.phone, { href: tel(h.phone), 'aria-label': `Call ${h.name}: ${h.phone}` }));
        const site = safeUrl(h.website);
        if (site) links.append(el('a', 'Website ↗', { href: site, target: '_blank', rel: 'noopener', 'aria-label': `${h.name} website (opens in a new tab)` }));
        const map = safeUrl(h.maps_url);
        if (map) links.append(el('a', 'Map ↗', { href: map, target: '_blank', rel: 'noopener', 'aria-label': `${h.name} on Google Maps (opens in a new tab)` }));
        if (links.childNodes.length) body.append(links);
        card.append(media, body);
        list.append(card);
      });
      box.append(list);
    }
    box.append(hotelMore(safeUrl(data.search_url) || hotelSearch(data.place)));
    (bubble.nextElementSibling?.classList.contains('chat-cards') ? bubble.nextElementSibling : bubble).after(box);
    pinTurn();
  }
  // Cards for the places Gemma named, under its answer, with the names in the answer linked to them.
  const CARD_STATUS = { available_now: 'Available now', advertised_vacancy: 'Vacancy advertised', upcoming: 'Coming soon', leasing: 'Now leasing', waitlist_open: 'Waitlist open', contact_for_availability: 'Call for availability' };
  let cardSeq = 0;
  const SHOWN = 2; // places an answer shows before "Show more"
  function chatCard(c, ids = {}) {
    const id = `chat-card-${++cardSeq}`;
    (c.names || [c.name.toLowerCase()]).forEach(k => { ids[k] = id; });
    const card = el('article', null, { class: 'chat-card', id, role: 'listitem', tabindex: '-1', 'aria-label': c.name });
    // Thumbnail: the provider's photo of this property, or (no photo, or one that won't load) a frosted map of its area,
    // never a stand-in photo of another place.
    const media = el('div', null, { class: 'chat-card-media', 'aria-hidden': 'true' });
    const mapThumb = () => { // homes: their area's map; shelters, legal aid and programs: a photo of the kind of place
      const art = placeholderArt(c.type, `${c.jurisdiction || ''} ${c.address || ''}`);
      media.replaceChildren();
      media.classList.add(art.map ? 'map-thumb' : 'stock-thumb');
      media.style.setProperty('--thumb', `url("${art.url}")`);
    };
    if (c.has_photo) { const img = el('img', null, { src: listingPhotoSrc(c.id, c.photo_url), alt: '', loading: 'lazy' });
      img.addEventListener('error', mapThumb, { once: true });
      media.append(img); } else mapThumb();
    const body = el('div', null, { class: 'chat-card-body' });
    const badge = CARD_STATUS[c.availability_status] || (c.waitlist_status === 'open' ? 'Waitlist open' : c.waitlist_status === 'closed' ? 'Waitlist closed' : null);
    if (badge) body.append(el('span', badge, { class: 'opt-badge' + (c.waitlist_status === 'closed' ? ' closed' : '') }));
    body.append(el('span', c.name, { class: 'chat-card-title' }));
    const meta = el('span', null, { class: 'chat-card-meta' });
    if (c.jurisdiction) meta.append(document.createTextNode(c.jurisdiction));
    if (typeof c.monthly_rent === 'number') { if (c.jurisdiction) meta.append(document.createTextNode(' · '));
      meta.append(el('b', ClearHomeRental.price(c))); } else if (c.rent_estimate) { if (c.jurisdiction) meta.append(document.createTextNode(' · ')); const est = el('b', `est. $${Math.round(c.rent_estimate.low).toLocaleString()}–$${Math.round(c.rent_estimate.high).toLocaleString()}/mo`);
      est.title = 'Estimate from ' + c.rent_estimate.basis + '. The provider sets the real rent.';
      meta.append(est); }
    if (meta.childNodes.length) body.append(meta);
    if (c.address) body.append(el('span', c.address, { class: 'chat-card-address' }));
    const links = el('div', null, { class: 'chat-card-actions' });
    if (c.phone) links.append(el('a', c.phone, { href: tel(c.phone), 'aria-label': `Call ${c.name}: ${c.phone}` }));
    const own = safeUrl(c.website);
    if (own && own !== c.source_url) links.append(el('a', 'Website ↗', { href: own, target: '_blank', rel: 'noopener', 'aria-label': `${c.name} website (opens in a new tab)` }));
    const site = safeUrl(c.source_url);
    if (site) links.append(el('a', 'Source ↗', { href: site, target: '_blank', rel: 'noopener', 'aria-label': `Source page for ${c.name} (opens in a new tab)` }));
    if (typeof c.lat === 'number') links.append(el('a', 'Map ↗', { href: `https://www.google.com/maps/search/?api=1&query=${c.lat},${c.lon}`, target: '_blank', rel: 'noopener', 'aria-label': `${c.name} on Google Maps (opens in a new tab)` }));
    const route = safeUrl(c.directions);
    if (route) links.append(el('a', 'Directions ↗', { href: route, target: '_blank', rel: 'noopener', 'aria-label': `Directions from ${c.name} to the place you asked about (opens in a new tab)` }));
    if (links.childNodes.length) body.append(links);
    card.append(media, body);
    return card;
  }

  function showCards(bubble, text, cards, shown = SHOWN) {
    const box = el('div', null, { class: 'chat-cards', role: 'list', 'aria-label': 'Places mentioned in this answer' });
    const ids = {};
    cards.forEach((c, n) => { const card = chatCard(c, ids); if (n >= shown) card.hidden = true;
      box.append(card); });
    box.cardsData = cards;
    bubble.after(box);
    pinTurn();
    if (shown) window.clearHomeMapFocus?.(cards, `Map shows the ${cards.length} place${cards.length === 1 ? '' : 's'} in this answer.`);
    // Turn each **name** in the answer into a link that brings its card into view. A list of more than two places shows
    // the first two; the rest wait behind "Show more" (showNext), like their cards.
    bubble.replaceChildren();
    let listed = 0;
    tidy(text).split('\n').forEach((line, i, all) => {
      const extra = line.startsWith('• ') && ++listed > SHOWN;
      const into = extra ? el('span', null, { class: 'chat-extra', hidden: '' }) : bubble;
      line.split(/(\*\*[^*]+\*\*)/).forEach(part => {
        if (!(part.startsWith('**') && part.endsWith('**'))) { into.append(document.createTextNode(part)); return; }
        const name = part.slice(2, -2),
          key = name.toLowerCase();
        const target = ids[key] || Object.entries(ids).find(([n]) => n.includes(key) || key.includes(n) || n.includes(`(${key})`))?.[1];
        if (!target) { into.append(el('strong', name)); return; }
        const a = el('a', null, { href: `#${target}`, class: 'chat-ref' });
        a.append(el('strong', name));
        a.addEventListener('click', e => { e.preventDefault(); const card = document.getElementById(target);
          card.hidden = false;
          card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
          card.focus({ preventScroll: true });
          card.classList.add('flash');
          setTimeout(() => card.classList.remove('flash'), 1200); });
        into.append(a);
      });
      if (i < all.length - 1) into.append(document.createTextNode('\n'));
      if (extra) bubble.append(into);
    });
  }
  // The map's "Near me" button asks here, sending the (rounded) location with this one question only.
  let oneShot = {};
  window.clearHomeAsk = (question, extra) => {
    oneShot = extra || {};
    document.getElementById('assistant-chips').hidden = true;
    document.getElementById('assistant').scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'center' });
    ask(question);
  };
  // Other parts of the page (like the live web search) post short updates here.
  window.clearHomeAssistantNote = text => { if (!log.querySelector('.msg')) return;
    botSay(text, 'update'); };

  // A field the search can't use gets a message beside it (read out by screen readers) instead of a quietly broader search.
  const fieldErrors = {
    show(id, message) {
      const input = document.getElementById(id),
        at = input.closest('.input-wrapper') || input;
      let note = document.getElementById(id + '-error');
      if (!note) { note = el('p', '', { id: id + '-error', class: 'field-error', role: 'alert' });
        at.after(note); }
      note.textContent = message;
      input.setAttribute('aria-invalid', 'true');
      input.setAttribute('aria-describedby', id + '-error');
      input.focus();
    },
    clear() {
      form.querySelectorAll('.field-error').forEach(n => n.remove());
      form.querySelectorAll('[aria-invalid]').forEach(n => { n.removeAttribute('aria-invalid');
        n.removeAttribute('aria-describedby'); });
    },
  };
  form.addEventListener('input', e => { if (e.target.hasAttribute('aria-invalid')) fieldErrors.clear(); });
  // The options panel's title, with an X that closes it and goes back to the "Need a Safe Place Tonight?" card.
  function resultsHead(title) {
    const x = el('button', null, { type: 'button', class: 'results-close', 'aria-label': 'Close these options' });
    x.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18"/></svg>';
    x.addEventListener('click', () => {
      results.hidden = true;
      results.replaceChildren();
      panelHotels.forEach(p => hotelsShown.delete(p));
      panelHotels.clear();
      document.getElementById('emergency').focus();
    });
    const head = el('div', null, { class: 'results-head' });
    head.append(el('h3', title), x);
    return head;
  }
  form.addEventListener('submit', async e => {
    e.preventDefault();
    // Blank budget or income means no limit; a number out of range, or one the browser couldn't read, is asked about.
    fieldErrors.clear();
    const wrong = [
        ['budget', 'Enter a monthly budget from $0 to $100,000, or leave it blank.'],
        ['income', 'Enter a yearly income from $0 to $10,000,000, or leave it blank.']
      ]
      .find(([id]) => { const f = document.getElementById(id).validity; return f.badInput || f.rangeUnderflow || f.rangeOverflow; });
    if (wrong) { fieldErrors.show(...wrong); return; }
    const v = id => document.getElementById(id).value.trim();
    const checked = id => document.getElementById(id).checked;
    profile = {
      location: v('location'),
      budget: v('budget') ? Number(v('budget')) : null,
      income: v('income') ? Number(v('income')) : null,
      household: v('household') ? Number(v('household')) : null,
      bedrooms: v('bedrooms') === '' ? null : Number(v('bedrooms')),
      timing: v('timing') || null,
      tonight: checked('tonight'),
      accessible: checked('accessible'),
      senior: checked('senior'),
      voucher: checked('voucher'),
      situation: v('situation')
    };
    const button = form.querySelector('button[type=submit]');
    button.disabled = true;
    results.hidden = false;
    results.replaceChildren(el('p', 'Finding your options…', { class: 'opt-empty' }));
    document.getElementById('location').dispatchEvent(new Event('change')); // the map zooms in; a web search is offered as a button
    try {
      const res = await fetch('/api/options', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(profile) });
      const data = await res.json();
      if (!res.ok || data.error) {
        const bad = Object.keys(data.fields || {}).find(id => document.getElementById(id));
        if (bad) fieldErrors.show(bad, data.fields[bad]);
        throw new Error(data.error || 'We could not load options.');
      }
      results.replaceChildren(resultsHead(profile.tonight ? `Tonight in ${data.area}` : `Your options in ${data.area}`));
      if (profile.tonight) {
        results.append(el('p', 'In danger right now? Call 911. For shelter tonight, call 211 or the intake line below. Don’t wait for an AI answer.', { class: 'notice-urgent' }));
        // Free shelters beside paid hotels, each column saying up front what it costs.
        const column = (box, tag, note) => { const h = box.querySelector('h4');
          h.append(el('span', ' · ', { class: 'visually-hidden' }), el('span', tag, { class: 'cost-tag ' + tag })); if (note) h.after(el('p', note, { class: 'hotel-note' }));
          box.classList.add('tonight-col', tag); return box; };
        const split = el('div', null, { class: 'tonight-split' });
        split.append(column(group('Shelters & Intake Lines', data.shelters, 'shelter', 'Call 211 for shelter tonight.'), 'free', 'No cost to stay. Call first: each card says how to get in.'),
          column(hotelGroup(profile.location || data.area), 'paid'));
        results.append(split);
      }
      const amenity = profile.tonight ? '' : v('find-amenity');
      let homeCount = data.listings.length;
      if (amenity) {
        // Homes with real walking times and a route map replace the plain list.
        homeCount = await window.runWalkSearch({
          location: profile.location,
          maxMonthlyRent: profile.budget || undefined,
          requiredAmenity: amenity,
          maxWalkingMinutes: Number(v('find-walk')),
          strict: !checked('find-walk-pref'),
          bedrooms: profile.bedrooms,
          senior: profile.senior,
          sort: 'best'
        });
      } else {
        window.clearWalkSearch();
        window.clearHomeMapFocus?.(data.listings, `Map shows the ${data.listings.length} homes that fit your choices.`);
        results.append(group('Homes You Could Apply For', data.listings, 'listing',
          `No reviewed listings match these choices in ${data.area}. Try a higher budget, any bedroom count, or a nearby area. Gemma is also searching the web; see the map above.`));
      }
      // Programs only when there's a sign the person needs them (income, voucher, tonight, or what they wrote).
      if (data.programs_relevant) {
        results.append(group('Programs That Can Help', data.programs, 'program', 'Call 211 for local programs.'));
      } else if (data.income_note) {
        results.append(el('p', data.income_note, { class: 'opt-empty' }));
      } else if (data.programs.length) {
        const more = el('button', 'Need help paying rent? Show assistance programs', { type: 'button', class: 'show-programs' });
        more.addEventListener('click', () => { more.replaceWith(group('Programs That Can Help', data.programs, 'program', 'Call 211 for local programs.')); });
        results.append(more);
      }
      // The assistant introduces itself once options are on screen; chatting is optional.
      cancelChat();
      log.replaceChildren();
      history = [];
      chat = {};
      chatInput.placeholder = PLACEHOLDER;
      turnStart = null;
      log.style.paddingBottom = '';
      log.classList.remove('chatting');
      document.getElementById('assistant-chips').hidden = true;
      const counts = [`${homeCount} home${homeCount === 1 ? '' : 's'}`];
      if (data.programs_relevant) counts.push(`${data.programs.length} program${data.programs.length === 1 ? '' : 's'}`);
      if (profile.tonight) counts.unshift(`${data.shelters.length} shelter option${data.shelters.length === 1 ? '' : 's'}`);
      botSay(`Hi, I'm the Clear Home assistant. I found ${counts.join(', ')} for ${data.area}. If you'd like, ask me anything about them, like which ones fit your income or how to apply.`);
      const extra = v('situation');
      if (extra) ask(extra);
    } catch (err) {
      results.replaceChildren(resultsHead('Your options'), el('p', err.message, { class: 'opt-empty' }));
    }
    button.disabled = false;
  });

  // Wake our Gemma GPU (it sleeps when nobody's using it) once the chat is on screen.
  const wake = new IntersectionObserver(entries => { if (entries.some(e => e.isIntersecting)) { wake.disconnect();
      fetch('/api/gemma/warm', { method: 'POST' }).catch(() => {}); } });
  wake.observe(document.getElementById('assistant'));
  const chips = document.getElementById('assistant-chips');
  chips.addEventListener('click', e => { const b = e.target.closest('button'); if (b) { chips.hidden = true;
      ask(b.textContent); } });
  // The greeting is the start screen above the message box ("Hi, I'm Gemma."); the log fills once someone writes.

  // "Pick an area" fills the box and moves the map there, the same as typing a place.
  document.getElementById('location-pick').addEventListener('change', e => {
    if (!e.target.value) return;
    const box = document.getElementById('location');
    box.value = e.target.value;
    e.target.value = '';
    window.clearHomeMapGoTo?.(box.value);
    window.clearHomeOfferWebSearch?.(box.value);
  });
  // Walking time and "nice to have" only mean something once a place to be near is chosen.
  const amenitySel = document.getElementById('find-amenity'),
    walkSel = document.getElementById('find-walk'),
    walkSoft = document.getElementById('find-walk-pref'),
    walkNote = document.getElementById('find-walk-note');

  function syncNearby() {
    const chosen = amenitySel.value;
    walkSel.disabled = walkSoft.disabled = !chosen;
    const label = amenitySel.selectedOptions[0].textContent;
    walkNote.textContent = chosen ? `${label} within a ${walkSel.value}-minute walk of the home${walkSoft.checked ? ' (nice to have)' : ''}.` : 'Choose a place to be near to set a walking time.';
    walkNote.classList.toggle('on', !!chosen);
  }
  [amenitySel, walkSel, walkSoft].forEach(x => x.addEventListener('change', syncNearby));
  syncNearby();
  document.querySelectorAll('[data-tonight]').forEach(b => b.addEventListener('click', () => {
    document.getElementById('location').value = b.dataset.tonight;
    document.getElementById('tonight').checked = true;
    form.requestSubmit();
    results.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' });
  }));
  // From the front page's "Need a place tonight?" chat: the same search, for the area picked there (read once).
  let tonightArea = null;
  try { tonightArea = sessionStorage.getItem('ch:tonight');
    sessionStorage.removeItem('ch:tonight'); } catch {}
  if (tonightArea) {
    document.getElementById('location').value = tonightArea.slice(0, 100);
    document.getElementById('tonight').checked = true;
    form.requestSubmit();
    setTimeout(() => results.scrollIntoView({ behavior: 'auto', block: 'start' }), 300);
  }

  chatForm.addEventListener('submit', e => { e.preventDefault(); const q = chatInput.value.trim(); if (!q || busy) return;
    chips.hidden = true;
    chatInput.value = '';
    ask(q); });
  chatInput.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault();
      chatForm.requestSubmit(); } });
  // The message box grows with what's typed, up to a few lines, like a messaging app.
  const fitInput = () => { chatInput.style.height = 'auto';
    chatInput.style.height = Math.min(chatInput.scrollHeight, 160) + 'px'; };
  chatInput.addEventListener('input', fitInput);
  chatForm.addEventListener('submit', () => setTimeout(fitInput));
  // A first question typed in the front page's "Get started" intro is waiting here: show the chat and send it right away.
  let firstQuestion = null;
  try { firstQuestion = sessionStorage.getItem('ch:first-question');
    sessionStorage.removeItem('ch:first-question'); } catch {}
  if (firstQuestion) { document.getElementById('assistant').scrollIntoView({ block: 'center' });
    chatInput.value = firstQuestion;
    chatForm.requestSubmit(); }
})();
