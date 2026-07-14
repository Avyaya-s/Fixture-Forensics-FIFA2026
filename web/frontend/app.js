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

let allMatches = [];
let scorerLabels = [];
let profiles = []; // [{key, label}]
let currentProfile = "balanced";
let activeGroups = new Set();
let activeMatchdays = new Set();
let searchTerm = "";
let sortKey = "match_id";
let sortDir = 1;

function getAverage(m) {
  return m.composites ? m.composites[currentProfile] : m.Average;
}

function currentProfileLabel() {
  return (profiles.find((p) => p.key === currentProfile) || {}).label || "Average";
}

async function init() {
  const [scorers, profileList, matches] = await Promise.all([
    fetchJSON("/api/scorers"),
    fetchJSON("/api/profiles"),
    fetchJSON("/api/matches"),
  ]);
  scorerLabels = scorers.map((s) => s.label);
  profiles = profileList;
  allMatches = matches;

  const groups = [...new Set(matches.map((m) => m.group))].sort();
  const matchdays = [...new Set(matches.map((m) => m.matchday))].sort((a, b) => a - b);
  activeGroups = new Set(groups);
  activeMatchdays = new Set(matchdays);

  renderRadioPills("profile-picker", profiles, currentProfile, (key) => {
    currentProfile = key;
    renderTableHead();
    render();
  });
  renderPills("group-filters", groups, activeGroups, render);
  renderPills("matchday-filters", matchdays, activeMatchdays, render, (d) => `MD ${d}`);

  document.getElementById("search").addEventListener("input", (e) => {
    searchTerm = e.target.value.trim().toLowerCase();
    render();
  });

  renderTableHead();
  render();
}

function renderPills(containerId, values, activeSet, onChange, formatFn) {
  const el = document.getElementById(containerId);
  el.innerHTML = "";
  values.forEach((v) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "pill" + (activeSet.has(v) ? " active" : "");
    btn.textContent = formatFn ? formatFn(v) : v;
    btn.addEventListener("click", () => {
      if (activeSet.has(v)) activeSet.delete(v);
      else activeSet.add(v);
      btn.classList.toggle("active");
      onChange();
    });
    el.appendChild(btn);
  });
}

function getFiltered() {
  return allMatches.filter(
    (m) =>
      activeGroups.has(m.group) &&
      activeMatchdays.has(m.matchday) &&
      (searchTerm === "" ||
        m.team_home.toLowerCase().includes(searchTerm) ||
        m.team_away.toLowerCase().includes(searchTerm))
  );
}

function render() {
  const filtered = getFiltered();
  renderStats(filtered);
  renderAvgChart(filtered);
  renderTableBody(filtered);
}

function renderStats(filtered) {
  const el = document.getElementById("stats");
  el.innerHTML = "";
  const withAvg = filtered.filter((m) => getAverage(m) != null);
  const avg = withAvg.length ? withAvg.reduce((s, m) => s + getAverage(m), 0) / withAvg.length : null;
  let lowest = null;
  withAvg.forEach((m) => {
    if (!lowest || getAverage(m) < getAverage(lowest)) lowest = m;
  });

  const avgBand = scoreBand(avg);
  const lowestBand = lowest ? scoreBand(getAverage(lowest)) : null;
  const tiles = [
    { label: "Matches shown", value: filtered.length },
    {
      label: `Avg score (${currentProfileLabel()})`,
      value: avg == null ? "–" : avg.toFixed(1),
      band: avgBand,
    },
    {
      label: "Lowest scoring fixture",
      value: lowest ? `${lowest.team_home} vs ${lowest.team_away}` : "–",
      sub: lowest ? `${getAverage(lowest).toFixed(1)} / 10` : "",
      band: lowestBand,
    },
  ];
  tiles.forEach((t) => {
    const div = document.createElement("div");
    div.className = "stat-tile" + (t.band ? ` status-${t.band.tier}` : "");
    const dot = t.band ? `<span class="status-dot status-${t.band.tier}" title="${t.band.label}"></span>` : "";
    div.innerHTML = `<div class="label">${dot}${t.label}</div><div class="value">${t.value}</div>${
      t.sub ? `<div class="sub">${t.sub}</div>` : ""
    }`;
    el.appendChild(div);
  });
}

function renderAvgChart(filtered) {
  const el = document.getElementById("avg-chart");
  if (!filtered.length) {
    el.innerHTML = `<div class="empty-state">No fixtures match the current filters.</div>`;
    return;
  }
  const items = scorerLabels.map((label) => {
    const vals = filtered.map((m) => m[label]).filter((v) => v != null);
    const avg = vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : null;
    return { label, value: avg, color: COLOR_BY_LABEL[label] || "var(--series-altitude)" };
  });
  renderBarChart(el, items, { max: 10 });
}

// Fixed per-column widths (see .col-* rules in style.css) so all 14 columns
// fit in one view with no horizontal scroll, instead of auto-sizing to
// content -- table-layout:fixed requires every column's width to be spoken
// for, which is also why fixture/venue truncate with an ellipsis + title
// tooltip rather than growing to fit the longest name.
function renderTableHead() {
  const tr = document.getElementById("table-head");
  const cols = [
    { key: "match_id", label: "ID", cls: "col-id" },
    { key: "group", label: "Grp", cls: "col-grp" },
    { key: "matchday", label: "MD", cls: "col-md" },
    { key: "fixture", label: "Fixture", cls: "col-fixture" },
    { key: "venue", label: "Venue", cls: "col-venue" },
    ...scorerLabels.map((l) => ({ key: l, label: l, cls: "col-score" })),
    { key: "Average", label: `Average (${currentProfileLabel()})`, cls: "col-average" },
  ];
  tr.innerHTML = "";
  cols.forEach((col) => {
    const th = document.createElement("th");
    th.textContent = col.label;
    th.className = col.cls;
    th.addEventListener("click", () => {
      if (sortKey === col.key) sortDir *= -1;
      else {
        sortKey = col.key;
        sortDir = 1;
      }
      renderTableHead();
      render();
    });
    if (sortKey === col.key) {
      th.classList.add("sorted");
      th.dataset.dir = sortDir === 1 ? "▲" : "▼";
    }
    tr.appendChild(th);
  });
}

function renderTableBody(filtered) {
  const tbody = document.getElementById("table-body");
  const rows = [...filtered].sort((a, b) => {
    const av = sortKey === "fixture" ? `${a.team_home} vs ${a.team_away}` : sortKey === "Average" ? getAverage(a) : a[sortKey];
    const bv = sortKey === "fixture" ? `${b.team_home} vs ${b.team_away}` : sortKey === "Average" ? getAverage(b) : b[sortKey];
    if (av == null) return 1;
    if (bv == null) return -1;
    if (typeof av === "string") return av.localeCompare(bv) * sortDir;
    return (av - bv) * sortDir;
  });

  tbody.innerHTML = "";
  if (!rows.length) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td colspan="${5 + scorerLabels.length + 1}"><div class="empty-state">No fixtures match the current filters.</div></td>`;
    tbody.appendChild(tr);
    return;
  }

  rows.forEach((m) => {
    const tr = document.createElement("tr");
    tr.addEventListener("click", () => {
      window.location.href = `match.html?id=${m.match_id}`;
    });
    const fixtureText = `${m.team_home} vs ${m.team_away}`;
    const cells = [
      { cls: "col-id", html: m.match_id },
      { cls: "col-grp", html: m.group },
      { cls: "col-md", html: m.matchday },
      { cls: "col-fixture", html: fixtureText, title: fixtureText },
      { cls: "col-venue", html: m.venue, title: m.venue },
      ...scorerLabels.map((l) => ({ cls: "col-score", html: meterCellHTML(m[l]) })),
      { cls: "col-average", html: statusMeterCellHTML(getAverage(m)) },
    ];
    tr.innerHTML = cells
      .map((c) => `<td class="${c.cls}"${c.title ? ` title="${c.title}"` : ""}>${c.html}</td>`)
      .join("");
    tbody.appendChild(tr);
  });
}

init().catch((err) => {
  document.querySelector(".page").innerHTML = `<div class="empty-state">Failed to load data: ${err.message}</div>`;
});
