// Open-source card: live GitHub stats.
// Used by the front page (/), frontend/about.html; runs where the page lists it.

// Live repository stats from GitHub's public API; the card still reads fine if this is blocked or rate-limited.
(async () => {
  const repo = 'phonehseng/clearhome',
    api = 'https://api.github.com/repos/' + repo;
  // GitHub allows 60 calls an hour per visitor, so answers are kept for an hour in this browser.
  const get = async u => {
    try { const hit = JSON.parse(localStorage.getItem('gh:' + u) || 'null'); if (hit && Date.now() - hit.at < 3600e3) return hit.data; } catch {}
    const r = await fetch(u, { headers: { Accept: 'application/vnd.github+json' } });
    if (!r.ok) throw r.status;
    const data = await r.json();
    try { localStorage.setItem('gh:' + u, JSON.stringify({ at: Date.now(), data })); } catch {}
    return data;
  };
  const el = (tag, attrs = {}, text) => { const n = document.createElement(tag);
    Object.entries(attrs).forEach(([k, v]) => n.setAttribute(k, v)); if (text != null) n.textContent = text; return n; };
  const TEAM = ['phonehseng', 'BUmair', 'pywhitaker-dev', 'r01984'];
  const team = document.getElementById('repo-team');
  const showTeam = users => team.replaceChildren(...users.map(p => { const a = el('a', { href: p.html_url, target: '_blank', rel: 'noopener' });
    a.append(el('img', { src: p.avatar_url + '&s=48', alt: '' }), document.createTextNode(p.login)); return a; }));
  const profile = login => ({ login, html_url: 'https://github.com/' + login, avatar_url: 'https://github.com/' + login + '.png?' });
  showTeam(TEAM.map(profile)); // the whole team shows even if GitHub's API is unreachable
  try {
    const [info, people, langs] = await Promise.all([get(api), get(api + '/contributors?per_page=20'), get(api + '/languages')]);
    const commits = people.reduce((n, p) => n + (p.contributions || 0), 0);
    const updated = new Date(info.pushed_at).toLocaleString([], { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
    const stats = document.getElementById('repo-stats');
    stats.replaceChildren();
    [
      [commits + '+', 'commits'],
      [Math.max(people.filter(p => p.type === 'User').length, 4), 'contributors'],
      ['Updated', updated],
      [info.stargazers_count, 'stars']
    ].forEach(([b, t]) => { const li = el('li');
      li.append(el('b', {}, String(b)), document.createTextNode(' ' + t));
      stats.append(li); });
    // The whole team always shows, even while GitHub's cached contributor list lags behind new pushes.
    const users = people.filter(p => p.type === 'User');
    TEAM.forEach(login => { if (!users.some(p => p.login.toLowerCase() === login.toLowerCase())) users.push(profile(login)); });
    showTeam(users);
    const total = Object.values(langs).reduce((a, b) => a + b, 0),
      colors = { Python: '#3572A5', HTML: '#e34c26', JavaScript: '#f1e05a', CSS: '#663399', Dockerfile: '#384d54' };
    const bar = document.getElementById('repo-langs'),
      key = document.getElementById('repo-langs-key');
    Object.entries(langs).forEach(([name, bytes]) => { const pct = bytes / total * 100; if (pct < 1) return;
      bar.append(el('span', { style: `width:${pct}%;background:${colors[name] || '#8b949e'}` }));
      key.append(el('span', {}, `${name} ${pct.toFixed(0)}%`)); });
  } catch { /* keep the static summary */ }
})();
