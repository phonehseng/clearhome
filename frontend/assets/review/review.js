// Verify, flag or hide listings.
// Used by the listing review page (/review), frontend/review.html; runs where the page lists it.

const $ = id => document.getElementById(id);
const el = (tag, text, attrs) => { const n = document.createElement(tag); if (text != null) n.textContent = text; for (const [k, v] of Object.entries(attrs || {})) n.setAttribute(k, v); return n; };
const safeUrl = u => { try { const x = new URL(u); return x.protocol === 'https:' ? x.href : null; } catch { return null; } };
const TYPES = { affordable_listing: 'Income-restricted home', rental_listing: 'Regular rental', affordable_property: 'Affordable property', emergency_shelter: 'Shelter', rental_assistance: 'Rent help', housing_authority: 'Housing program', legal_aid: 'Legal aid', food_support: 'Food', other: 'Other' };
const STATUS = { available_now: 'Available now', advertised_vacancy: 'Vacancy advertised', upcoming: 'Coming soon', leasing: 'Now leasing', waitlist_open: 'Waitlist open', contact_for_availability: 'Call for availability', closed: 'Closed' };
const STATE_LABEL = { verified: 'Verified by team', flagged: 'Flagged', hidden: 'Hidden' };
let records = [],
  decisions = {},
  canEdit = false,
  page = 60,
  quick = '';

function stateOf(r) { return decisions[r.id]?.state || 'none'; }

function matches(r) {
  const q = $('q').value.trim().toLowerCase(),
    want = $('state').value || quick;
  if (q && ![r.id, r.name, r.community, r.phone, r.address, r.jurisdiction, decisions[r.id]?.note].some(v => String(v || '').toLowerCase().includes(q))) return false;
  if ($('region').value && (r.region || 'Other') !== $('region').value) return false;
  if ($('type').value && r.type !== $('type').value) return false;
  if (want === 'problems') return r.problems.length > 0;
  if (want === 'notshown') return !r.shown;
  if (want === 'due') return r.availability.review_due && r.availability.review_due < new Date().toISOString().slice(0, 10);
  return !want || stateOf(r) === want;
}

function card(r) {
  const state = stateOf(r),
    d = decisions[r.id];
  const box = el('article', null, { class: 'rec', 'data-state': state });
  const head = el('div');
  head.append(el('h3', r.name), el('div', r.id, { class: 'id' }));
  const tags = el('div', null, { class: 'tags' });
  tags.append(el('span', TYPES[r.type] || r.type || 'No type', { class: 'tag' }));
  if (r.availability.status) tags.append(el('span', STATUS[r.availability.status] || r.availability.status, { class: 'tag' }));
  if (!r.shown) tags.append(el('span', 'Not shown to users', { class: 'tag bad' }));
  if (r.problems.length) tags.append(el('span', `${r.problems.length} data problem${r.problems.length > 1 ? 's' : ''}`, { class: 'tag bad' }));
  if (state !== 'none') tags.append(el('span', STATE_LABEL[state], { class: 'tag ' + ({ verified: 'ok', flagged: 'warn', hidden: 'bad' })[state] }));
  box.append(head, tags);
  const facts = el('div', null, { class: 'facts' });
  [r.address || [r.area, r.jurisdiction].filter(Boolean).join(' · '), r.phone && '☎ ' + r.phone,
    typeof r.monthly_rent === 'number' && `$${r.monthly_rent.toLocaleString('en-US',{maximumFractionDigits:0})}/mo`, r.minimum_age && `${r.minimum_age}+`,
    r.last_verified && `verified ${r.last_verified}`, r.availability.review_due && `recheck by ${r.availability.review_due}`,
    r.lat == null && 'no map location', r.has_photo && 'photo'
  ].filter(Boolean).forEach(t => facts.append(el('span', t)));
  const link = safeUrl(r.source_url);
  if (link) { const a = el('a', 'Source ↗', { href: link, target: '_blank', rel: 'noopener' });
    facts.append(a); }
  box.append(facts);
  if (r.availability.evidence) box.append(el('p', r.availability.evidence, { class: 'evidence' }));
  if (r.problems.length) box.append(el('p', 'Data problems: ' + r.problems.join('; '), { class: 'note', 'data-state': 'hidden' }));
  if (d && (d.note || state !== 'none')) box.append(el('p', `${STATE_LABEL[state]} ${d.on || ''}${d.note ? ': ' + d.note : ''}`, { class: 'note', 'data-state': state }));
  const actions = el('div', null, { class: 'actions' });
  const button = (label, cls, next) => {
    const b = el('button', label, { type: 'button', class: cls });
    b.disabled = !canEdit;
    if (!canEdit) b.title = 'Saving works on a local copy only';
    b.addEventListener('click', () => decide(r, next, b));
    actions.append(b);
  };
  if (state !== 'verified') button('Verify', 'verify', 'verified');
  button(state === 'flagged' ? 'Edit flag note' : 'Flag', 'flag', 'flagged');
  if (state !== 'hidden') button('Hide', 'hide', 'hidden');
  if (state !== 'none') button(state === 'hidden' ? 'Unhide' : 'Clear', '', 'clear');
  box.append(actions);
  return box;
}

async function decide(r, state, button) {
  let note = decisions[r.id]?.note || '';
  if (state === 'flagged' || state === 'hidden') {
    const asked = prompt(state === 'hidden' ? 'Why hide it? (shown to the team only)' : 'What needs checking?', note);
    if (asked === null) return;
    note = asked;
  } else if (state === 'verified') {
    const asked = prompt('How did you verify it? (e.g. "called 10/25, rent confirmed")', '');
    if (asked === null) return;
    note = asked;
  }
  button.disabled = true;
  try {
    const res = await fetch('/api/review', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: r.id, state, note }) });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Could not save.');
    decisions = data.decisions;
    render(false);
  } catch (e) { alert(e.message);
    button.disabled = false; }
}

function stats() {
  const today = new Date().toISOString().slice(0, 10);
  const n = f => records.filter(f).length;
  const items = [
    ['', 'All records', records.length],
    ['none', 'Not reviewed', n(r => stateOf(r) === 'none')],
    ['flagged', 'Flagged', n(r => stateOf(r) === 'flagged')],
    ['verified', 'Verified', n(r => stateOf(r) === 'verified')],
    ['hidden', 'Hidden', n(r => stateOf(r) === 'hidden')],
    ['problems', 'Data problems', n(r => r.problems.length)],
    ['notshown', 'Not shown', n(r => !r.shown)],
    ['due', 'Recheck overdue', n(r => r.availability.review_due && r.availability.review_due < today)]
  ];
  $('stats').replaceChildren(...items.map(([key, label, count]) => {
    const b = el('button', null, { type: 'button', class: 'stat', 'aria-pressed': String(quick === key && !$('state').value) });
    b.append(el('strong', String(count)), label);
    b.addEventListener('click', () => { quick = key;
      $('state').value = '';
      page = 60;
      render(); });
    return b;
  }));
}

function render(resetPage = true) {
  if (resetPage) page = 60;
  stats();
  const shown = records.filter(matches);
  $('count').textContent = `${shown.length} of ${records.length} records`;
  const list = $('list');
  list.replaceChildren(...shown.slice(0, page).map(card));
  if (shown.length > page) {
    const more = el('button', `Show ${Math.min(60, shown.length - page)} More`, { type: 'button', class: 'more' });
    more.addEventListener('click', () => { page += 60;
      render(false); });
    list.append(more);
  }
}

fetch('/api/review').then(r => r.json()).then(data => {
  records = data.records || [];
  decisions = data.decisions || {};
  canEdit = !!data.can_edit;
  // Flagged first, then anything with data problems, then the rest by name.
  const rank = r => ({ flagged: 0, hidden: 3, verified: 4 })[stateOf(r)] ?? (r.problems.length || !r.shown ? 1 : 2);
  records.sort((a, b) => rank(a) - rank(b) || a.name.localeCompare(b.name));
  [...new Set(records.map(r => r.region || 'Other'))].sort().forEach(v => $('region').append(new Option(v, v)));
  [...new Set(records.map(r => r.type).filter(Boolean))].sort().forEach(v => $('type').append(new Option(TYPES[v] || v, v)));
  if (!canEdit) { $('banner').hidden = false;
    $('banner').textContent = 'View only. To save decisions, run the app on your own computer (python backend/app.py), open http://localhost:8000/review, then commit data/listing_review.json and redeploy.'; }
  render();
}).catch(() => { $('count').textContent = 'Could not load the catalog.'; });
for (const id of ['q', 'region', 'type', 'state']) $(id).addEventListener('input', () => { if (id === 'state') quick = '';
  render(); });
