// Resources chat, programs and rentals.
// Used by the resources page (/resources), frontend/resources.html; runs where the page lists it.

const el = (tag, attrs = {}, text) => {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  if (text != null) node.textContent = text;
  return node;
};
const safeUrl = url => typeof url === 'string' && url.startsWith('https://') ? url : null;

// Ask the AI. Answers are rendered as text, with **bold** turned into <strong> safely.
const chat = document.getElementById('chat');
const form = document.getElementById('ask-form');
const input = document.getElementById('question');
const history = [];

function addMessage(role, text, state) {
  const msg = el('div', { class: `msg ${role}` });
  if (state) msg.dataset.state = state;
  text.split(/(\*\*[^*]+\*\*)/).forEach(part => {
    msg.append(part.startsWith('**') && part.endsWith('**') ? el('strong', {}, part.slice(2, -2)) : document.createTextNode(part));
  });
  chat.append(msg);
  chat.scrollTop = chat.scrollHeight;
  return msg;
}
form.addEventListener('submit', async e => {
  e.preventDefault();
  const question = input.value.trim();
  if (!question) return;
  const button = form.querySelector('button');
  addMessage('user', question);
  input.value = '';
  button.disabled = true;
  const pending = addMessage('assistant', 'Thinking it through. This usually takes 20 to 40 seconds…', 'loading');
  const started = Date.now();
  const timer = setInterval(() => { pending.textContent = `Thinking it through. This usually takes 20 to 40 seconds… (${Math.round((Date.now() - started) / 1000)}s)`; }, 1000);
  try {
    const res = await fetch('/api/ask', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question, history }) });
    const data = await res.json();
    clearInterval(timer);
    pending.remove();
    if (!res.ok || data.error) throw new Error(data.error || 'Something went wrong.');
    addMessage('assistant', data.answer);
    history.push({ role: 'user', text: question }, { role: 'assistant', text: data.answer });
  } catch (err) {
    clearInterval(timer);
    pending.remove();
    const msg = err.message || 'We could not reach the assistant.';
    addMessage('assistant', /211/.test(msg) ? msg : msg + ' For urgent help, call 211.', 'error'); // the server's message may already say 211
  }
  button.disabled = false;
  input.focus();
});
input.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault();
    form.requestSubmit(); } });
document.querySelectorAll('.examples button').forEach(b => b.addEventListener('click', () => { input.value = b.textContent;
  form.requestSubmit(); }));

// Programs, grouped by type and filterable by area.
const GROUPS = [
  ['housing_authority', 'Vouchers and public housing'],
  ['rental_assistance', 'Help paying rent'],
  ['legal_aid', 'Free legal help'],
  ['other', 'Other help and information']
];
const WAITLIST = { open: ['Waitlist open', 'open'], closed: ['Waitlist closed', 'closed'], unknown: ['Waitlist status unknown', ''] };
let allPrograms = [];

function programCard(p, rank) {
  const card = el('article', { class: rank ? 'item ranked' : 'item' });
  if (rank === 1) card.append(el('span', { class: 'badge fit' }, 'Best fit'));
  if (p.waitlist_status && WAITLIST[p.waitlist_status]) {
    const [label, cls] = WAITLIST[p.waitlist_status];
    card.append(el('span', { class: `badge ${cls}` }, label));
  }
  card.append(el('h3', {}, p.name));
  card.append(el('span', { class: 'meta' }, p.jurisdiction));
  if (p.who_it_serves) card.append(el('p', {}, p.who_it_serves));
  if (p.how_to_apply || p.requirements) {
    const details = el('details');
    details.append(el('summary', {}, 'How to Apply'));
    if (p.requirements) details.append(el('p', {}, 'Who qualifies: ' + p.requirements));
    if (p.how_to_apply) details.append(el('p', {}, p.how_to_apply));
    card.append(details);
  }
  const actions = el('div', { class: 'actions' });
  if (p.phone) actions.append(el('a', { href: ClearHomeDial(p.phone) }, p.phone));
  // Say where each link goes: a program page, an official county listing, or the provider's website.
  const links = Array.isArray(p.links) && p.links.length ? p.links : [
    { url: p.source_url, label: p.source_kind === 'official_directory' || /directory|guide|emergency-shelters/i.test(p.source_url || '') ? 'Official county listing' : 'Program details' },
    { url: p.website, label: 'Provider website' }
  ];
  const seen = new Set();
  links.forEach(l => { if (safeUrl(l.url) && !seen.has(l.url)) { seen.add(l.url);
      actions.append(el('a', { href: l.url, target: '_blank', rel: 'noopener', title: l.note || '' }, l.label + ' ↗')); } });
  card.append(actions);
  return card;
}

function shownPrograms() {
  const area = document.getElementById('area').value;
  return allPrograms.filter(p => !area || p.jurisdiction === area || (p.service_areas || []).includes(area) || (area !== 'Blacksburg' && p.jurisdiction === 'Northern Virginia'));
}
function renderPrograms() {
  const box = document.getElementById('programs');
  box.replaceChildren();
  const shown = shownPrograms();
  // Gemma's sort: its picks first, best fit first, then everything else in the usual groups.
  const picks = (ranked || []).map(id => shown.find(p => p.id === id)).filter(Boolean);
  if (picks.length) {
    box.append(el('h3', { class: 'group-title' }, `Best fits for “${sortQuestion}”`));
    const grid = el('div', { class: 'grid' });
    picks.forEach((p, n) => grid.append(programCard(p, n + 1)));
    box.append(grid);
  }
  for (const [type, title] of GROUPS) {
    const items = shown.filter(p => p.type === type && !picks.includes(p));
    if (!items.length) continue;
    box.append(el('h3', { class: 'group-title' }, title));
    const grid = el('div', { class: 'grid' });
    items.forEach(p => grid.append(programCard(p)));
    box.append(grid);
  }
  if (!box.children.length) box.append(el('p', { class: 'empty' }, 'No programs for this area yet. Call 211 for local help.'));
}
fetch('/api/programs').then(r => r.json()).then(data => {
  allPrograms = data.programs || [];
  const select = document.getElementById('area');
  [...new Set(allPrograms.map(p => p.jurisdiction))].filter(j => j !== 'Northern Virginia').sort()
    .forEach(j => select.append(el('option', { value: j }, j)));
  select.addEventListener('change', () => { resetSort();
    loadResourceHousing(); });
  renderPrograms();
}).catch(() => { document.getElementById('programs').replaceChildren(el('p', { class: 'empty' }, 'Could not load programs. Call 211 for local help.')); });

// Gemma sorts the programs at the top of the page. Two calls, so it feels instant: the first returns an order from the
// words right away; the second has Gemma order them and say why (a repeated question comes back from its memory).
const sortForm = document.getElementById('sort-form');
const sortInput = document.getElementById('sort-input');
const sortReply = document.getElementById('sort-reply');
const sortText = document.getElementById('sort-text');
const sortPicks = document.getElementById('sort-picks');
const sortReset = document.getElementById('sort-reset');
const SORT_HINT = sortText.textContent;
let ranked = null, sortQuestion = '', sortRun = 0;

function showSort(result) {
  ranked = result.order || [];
  sortText.textContent = result.note || '';
  sortReset.hidden = false;
  renderPrograms();
  const shown = shownPrograms();
  const top = ranked.map(id => shown.find(p => p.id === id)).filter(Boolean).slice(0, 3);
  sortPicks.replaceChildren();
  sortPicks.hidden = !top.length;
  if (!top.length) return;
  const grid = el('div', { class: 'grid' });
  top.forEach((p, n) => grid.append(programCard(p, n + 1)));
  const all = el('a', { class: 'sort-all', href: '#programs-section' }, `See all ${shown.length} programs, best fits first ↓`);
  sortPicks.append(grid, all);
}
function resetSort() {
  sortRun++;
  ranked = null;
  sortQuestion = '';
  sortText.textContent = SORT_HINT;
  delete sortReply.dataset.state;
  sortReset.hidden = true;
  sortPicks.hidden = true;
  sortPicks.replaceChildren();
  renderPrograms();
}
async function sortPrograms(question) {
  const run = ++sortRun;
  sortQuestion = question;
  const ids = shownPrograms().map(p => p.id);
  if (!ids.length) { sortText.textContent = 'Programs are still loading. Try again in a moment.'; return; }
  sortReply.dataset.state = 'loading';
  sortText.textContent = 'Sorting…';
  const call = quick => fetch('/api/programs/sort', { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, ids, quick }) }).then(r => r.json().then(data => { if (!r.ok || data.error) throw new Error(data.error); return data; }));
  try {
    const first = await call(true);
    if (run !== sortRun) return;
    showSort(first);
    if (!first.final) {
      const second = await call(false);
      if (run !== sortRun) return;
      showSort(second);
    }
  } catch (err) {
    if (run === sortRun) sortText.textContent = err.message || 'Sorting didn’t work just now. Try again, or browse the programs below.';
  }
  if (run === sortRun) delete sortReply.dataset.state;
}
sortForm.addEventListener('submit', e => {
  e.preventDefault();
  const question = sortInput.value.trim();
  if (question) sortPrograms(question);
});
document.querySelectorAll('.sort-chip[data-q]').forEach(b => b.addEventListener('click', () => { sortInput.value = b.dataset.q;
  sortPrograms(b.dataset.q); }));
sortReset.addEventListener('click', () => { sortInput.value = '';
  resetSort(); });

// A few current listings.
const STATUS = { available_now: 'Available now', advertised_vacancy: 'Vacancy advertised', upcoming: 'Coming soon', leasing: 'Now leasing', waitlist_open: 'Waitlist open', contact_for_availability: 'Call for availability' };

function loadResourceHousing() {
  const params = new URLSearchParams({ group_by: 'community', sort: 'rent_asc', age_group: document.getElementById('resource-age-group').value });
  const area = document.getElementById('area').value;
  if (area) params.set('location', area);
  fetch('/api/listings?' + params.toString()).then(r => r.json()).then(data => {
    const box = document.getElementById('listings');
    box.replaceChildren();
    (data.listings || []).slice(0, 8).forEach(l => {
      const card = el('article', { class: 'item' });
      const plans = l.floor_plans ? l.floor_plans.map(p => ({ ...l, ...p })) : [l];
      const statuses = new Set(plans.map(p => p.availability?.status));
      card.append(el('span', { class: 'badge' }, statuses.size > 1 ? 'Availability varies by plan' : STATUS[l.availability?.status] || 'Check availability'));
      card.append(el('h3', {}, l.community || l.name));
      card.append(el('span', { class: 'meta' }, [l.city, l.jurisdiction].filter(Boolean).join(' · ')));
      if (typeof l.monthly_rent === 'number') card.append(el('span', { class: 'rent' }, ClearHomeRental.price(l)));
      if (plans.length > 1) card.append(el('p', {}, `${plans.length} matching floor plans. Starting rent shown for the lowest-priced plan; eligibility and fees vary.`));
      if (l.who_it_serves) card.append(el('p', {}, l.who_it_serves));
      const actions = el('div', { class: 'actions' });
      if (l.phone) actions.append(el('a', { href: ClearHomeDial(l.phone) }, l.phone));
      const site = safeUrl(l.source_url);
      if (site) actions.append(el('a', { href: site, target: '_blank', rel: 'noopener' }, 'Provider Page'));
      card.append(actions);
      box.append(card);
    });
    if (!box.children.length) box.append(el('p', { class: 'empty' }, 'No current listings. Check back soon or call 211.'));
  }).catch(() => { document.getElementById('listings').replaceChildren(el('p', { class: 'empty' }, 'Could not load listings.')); });
}
document.getElementById('resource-age-group').addEventListener('change', loadResourceHousing);
loadResourceHousing();
