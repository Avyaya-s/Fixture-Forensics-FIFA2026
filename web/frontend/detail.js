const COLOR_BY_LABEL = {
  "Altitude": "var(--series-altitude)",
  "Travel": "var(--series-travel)",
  "Jet Lag": "var(--series-jetlag)",
  "Venue Fit": "var(--series-venue)",
  "Broadcast": "var(--series-broadcast)",
  "Climate": "var(--series-climate)",
  "Air Quality": "var(--series-airquality)",
  "Cross-Border": "var(--series-crossborder)",
};

const LABEL_BY_KEY = {
  altitude_fairness: "Altitude",
  travel_fairness: "Travel",
  jet_lag: "Jet Lag",
  venue_fit: "Venue Fit",
  broadcast_reach: "Broadcast",
  climate_risk: "Climate",
  air_quality: "Air Quality",
  cross_border: "Cross-Border",
};

let profiles = []; // [{key, label}]
let currentProfile = "balanced";
let currentSummary = null;

async function init() {
  const [profileList, matches] = await Promise.all([fetchJSON("/api/profiles"), fetchJSON("/api/matches")]);
  profiles = profileList;

  const select = document.getElementById("match-select");
  select.innerHTML = matches
    .map((m) => `<option value="${m.match_id}">${m.match_id} — ${m.team_home} vs ${m.team_away}</option>`)
    .join("");

  const requestedId = new URLSearchParams(window.location.search).get("id");
  const initialId = matches.some((m) => m.match_id === requestedId) ? requestedId : matches[0].match_id;
  select.value = initialId;

  renderRadioPills("detail-profile-picker", profiles, currentProfile, (key) => {
    currentProfile = key;
    renderCompositeHero();
  });

  select.addEventListener("change", () => loadMatch(select.value));
  await loadMatch(initialId);
}

async function loadMatch(matchId) {
  history.replaceState(null, "", `match.html?id=${matchId}`);
  const data = await fetchJSON(`/api/matches/${matchId}`);
  currentSummary = data.summary;
  renderMeta(data.match);
  renderCompositeHero();
  renderScoreCards(data.scores);
  renderComparisonChart(data.scores);
  document.getElementById("raw-json").textContent = JSON.stringify(data.scores, null, 2);
}

function renderCompositeHero() {
  const el = document.getElementById("composite-hero");
  const value = currentSummary ? currentSummary.composites[currentProfile] : null;
  const band = scoreBand(value);
  const profileLabel = (profiles.find((p) => p.key === currentProfile) || {}).label || "";
  if (value == null) {
    el.innerHTML = `<div class="hero-band">N/A for this lens</div>`;
    return;
  }
  el.innerHTML = `
    <div class="hero-value">${value.toFixed(1)}<span style="font-size:1rem; color:var(--text-muted);">/10</span></div>
    <div class="hero-band"><span class="status-dot status-${band.tier}"></span>${band.label} · ${profileLabel}</div>
  `;
}

function renderMeta(match) {
  document.getElementById("meta-line").textContent =
    `${match.venue_name}, ${match.venue_city} · ${match.date} kickoff ${match.kickoff_local} local ` +
    `· Group ${match.group}, Matchday ${match.matchday}`;
}

function renderScoreCards(scores) {
  const el = document.getElementById("score-cards");
  el.innerHTML = "";
  Object.entries(scores).forEach(([key, result]) => {
    const label = LABEL_BY_KEY[key] || result.scorer;
    const color = COLOR_BY_LABEL[label] || "var(--series-altitude)";
    const band = scoreBand(result.goodness);
    const goodnessNote =
      result.scale === "risk" && result.goodness != null
        ? `<div class="reasoning">Counts as ${result.goodness.toFixed(1)}/10 goodness toward the average (risk, inverted).</div>`
        : "";
    const card = document.createElement("div");
    card.className = "score-card";
    card.style.setProperty("--accent", color);
    card.innerHTML = `
      <div class="label"><span class="swatch" style="background:${color}; display:inline-block; width:9px; height:9px; border-radius:2px;"></span>${label}</div>
      <div class="score">${band ? `<span class="status-dot status-${band.tier}" title="${band.label}"></span>` : ""}${result.label}</div>
      <div class="reasoning">${result.reasoning}</div>
      ${goodnessNote}
    `;
    el.appendChild(card);
  });
}

function renderComparisonChart(scores) {
  // Plotted on the shared higher-is-better "goodness" scale -- climate_risk's
  // native score is risk (higher = worse), so plotting it unconverted would
  // make a longer bar look "better" on that axis while meaning the opposite.
  const el = document.getElementById("detail-chart");
  const items = Object.entries(scores).map(([key, result]) => {
    const label = LABEL_BY_KEY[key] || result.scorer;
    return { label, value: result.goodness, color: COLOR_BY_LABEL[label] || "var(--series-altitude)" };
  });
  renderBarChart(el, items, { max: 10 });
}

init().catch((err) => {
  document.querySelector(".page").innerHTML = `<div class="empty-state">Failed to load data: ${err.message}</div>`;
});
