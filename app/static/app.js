const $ = (id) => document.getElementById(id);

async function getJSON(url, options) {
  const res = await fetch(url, options);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

function option(value, label) {
  const el = document.createElement('option');
  el.value = value;
  el.textContent = label;
  return el;
}

async function loadHealth() {
  try {
    const h = await getJSON('/health');
    $('healthCard').innerHTML = `<b>${h.app || 'APEX'}</b><br>Status: ${h.status}<br>Providers: ${JSON.stringify(h.providers || {})}`;
  } catch (e) {
    $('healthCard').textContent = 'Statut indisponible';
  }
}

async function loadCountries() {
  const data = await getJSON('/api/countries');
  const list = data.countries || [];
  $('country').innerHTML = '';
  list.forEach(c => $('country').appendChild(option(c.name || c.country || c, c.name || c.country || c)));
  await loadLeagues();
}

async function loadLeagues() {
  const country = $('country').value;
  const season = $('season').value || new Date().getFullYear();
  const data = await getJSON(`/api/leagues?country=${encodeURIComponent(country)}&season=${season}`);
  const list = data.leagues || [];
  $('league').innerHTML = '';
  list.forEach(x => {
    const league = x.league || x;
    const opt = option(league.name || league, league.name || league);
    if (league.id) opt.dataset.id = league.id;
    $('league').appendChild(opt);
  });
  const selected = $('league').selectedOptions[0];
  if (selected && selected.dataset.id) $('leagueId').value = selected.dataset.id;
}

$('country').addEventListener('change', loadLeagues);
$('league').addEventListener('change', () => {
  const selected = $('league').selectedOptions[0];
  $('leagueId').value = selected?.dataset?.id || '';
});

function pct(x) { return `${Math.round((x || 0) * 1000) / 10}%`; }

function renderReport(r) {
  const p = r.probabilities;
  const primary = r.primary_bet;
  const signals = (r.market_signals || []).slice(0, 12);
  $('result').classList.remove('hidden');
  $('result').innerHTML = `
    <h2>Résultat</h2>
    <span class="verdict ${r.final_verdict}">${r.final_verdict}</span>
    <div class="summary-grid">
      <div class="metric"><div class="label">Qualité données</div><div class="value">${pct(r.data_quality.score)}</div></div>
      <div class="metric"><div class="label">Home win</div><div class="value">${pct(p.home_win)}</div></div>
      <div class="metric"><div class="label">Draw</div><div class="value">${pct(p.draw)}</div></div>
      <div class="metric"><div class="label">Away win</div><div class="value">${pct(p.away_win)}</div></div>
    </div>
    <div class="blocks">
      <div class="block"><h3>Pari principal</h3>${primary ? `<p><b>${primary.market}</b> / ${primary.selection}</p><p>Probabilité: ${pct(primary.probability)} | Fair odds: ${primary.fair_odds} | Cote: ${primary.best_odds || '-'}</p><p>Edge: ${primary.edge ?? '-'} | ROI: ${primary.roi_estimate ?? '-'}</p>` : '<p>Aucun pari principal validé.</p>'}</div>
      <div class="block"><h3>Council</h3><p>${r.council.recommendation}</p><p><b>Action:</b> ${r.council.first_action}</p></div>
    </div>
    <h3>Signaux marchés</h3>
    <table><thead><tr><th>Marché</th><th>Sélection</th><th>Proba</th><th>Fair odds</th><th>Cote</th><th>Edge</th><th>Status</th></tr></thead><tbody>
      ${signals.map(s => `<tr><td>${s.market}</td><td>${s.selection}</td><td>${pct(s.probability)}</td><td>${s.fair_odds}</td><td>${s.best_odds || '-'}</td><td>${s.edge ?? '-'}</td><td><span class="tag">${s.status}</span></td></tr>`).join('')}
    </tbody></table>
    <h3>Scores probables</h3>
    <pre>${JSON.stringify(p.most_likely_scores, null, 2)}</pre>
    <h3>Avertissements</h3>
    <pre>${JSON.stringify(r.warnings || [], null, 2)}</pre>
  `;
}

$('analysisForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  $('result').classList.remove('hidden');
  $('result').innerHTML = '<h2>Analyse en cours...</h2>';
  const payload = {
    match_date: $('matchDate').value,
    country: $('country').value,
    league: $('league').value,
    home: $('home').value,
    away: $('away').value,
    season: $('season').value ? Number($('season').value) : null,
    league_id: $('leagueId').value ? Number($('leagueId').value) : null,
    risk_profile: $('riskProfile').value
  };
  try {
    const report = await getJSON('/api/analyze', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    renderReport(report);
  } catch (err) {
    $('result').innerHTML = `<h2>Erreur</h2><pre>${err.message}</pre>`;
  }
});

(function init(){
  const today = new Date().toISOString().slice(0,10);
  $('matchDate').value = today;
  $('season').value = new Date().getFullYear();
  loadHealth();
  loadCountries();
})();
