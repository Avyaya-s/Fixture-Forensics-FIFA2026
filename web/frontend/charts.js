// Hand-built SVG/HTML chart primitives -- no charting library, per the
// project's no-build-step frontend. Bars: <=24px thick, 4px rounded tip,
// square baseline; gridline every 20% of max (2 units on a 0-10 scale).
// Shared by both pages (index.html and match.html both load this file).

// Single-select pill row (radio-button behavior), e.g. the weight-profile
// lens toggle on both pages.
function renderRadioPills(containerId, options, activeKey, onChange) {
  const el = document.getElementById(containerId);
  el.innerHTML = "";
  options.forEach((opt) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "pill" + (opt.key === activeKey ? " active" : "");
    btn.textContent = opt.label;
    btn.addEventListener("click", () => {
      // Checks the button's live DOM state, not the `activeKey` parameter --
      // that parameter is only the *initial* selection and never updates,
      // so comparing against it directly would make re-selecting whichever
      // option started active silently do nothing after switching away.
      if (btn.classList.contains("active")) return;
      [...el.children].forEach((c) => c.classList.remove("active"));
      btn.classList.add("active");
      onChange(opt.key);
    });
    el.appendChild(btn);
  });
}

function renderBarChart(container, items, opts = {}) {
  const max = opts.max ?? 10;
  container.innerHTML = "";
  const wrap = document.createElement("div");
  wrap.className = "barchart";

  items.forEach((item) => {
    const row = document.createElement("div");
    row.className = "bar-row";

    const label = document.createElement("div");
    label.className = "bar-label";
    const swatch = document.createElement("span");
    swatch.className = "swatch";
    swatch.style.background = item.color;
    label.appendChild(swatch);
    label.appendChild(document.createTextNode(item.label));

    const track = document.createElement("div");
    track.className = "bar-track";
    const fill = document.createElement("div");
    fill.className = "bar-fill";
    const pct = item.value == null ? 0 : Math.max(0, Math.min(100, (item.value / max) * 100));
    fill.style.width = `${pct}%`;
    fill.style.background = item.color;
    track.appendChild(fill);

    track.addEventListener("mousemove", (evt) => {
      const text = item.value == null ? "N/A" : `${item.value.toFixed(1)} / ${max}`;
      showTooltip(evt, `<strong>${item.label}</strong><br>${text}`);
    });
    track.addEventListener("mouseleave", hideTooltip);

    const value = document.createElement("div");
    value.className = "bar-value";
    value.textContent = item.value == null ? "–" : item.value.toFixed(1);

    row.appendChild(label);
    row.appendChild(track);
    row.appendChild(value);
    wrap.appendChild(row);
  });

  container.appendChild(wrap);
}

function meterCellHTML(value, max = 10) {
  if (value === null || value === undefined) {
    return `<span class="na">—</span>`;
  }
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  return `<div class="meter-cell">
    <div class="meter-track"><div class="meter-fill" style="width:${pct}%"></div></div>
    <div class="meter-value">${value.toFixed(1)}</div>
  </div>`;
}

// Maps a 0-10 goodness score to a status tier for fast visual scanning.
// This is a display convenience, not a cited threshold like WBGT/AQI --
// unlike those, these band edges (8/6/4) aren't backed by a published
// standard, just a reasonable split for "which numbers need attention."
function scoreBand(value) {
  if (value == null) return null;
  if (value >= 8) return { tier: "good", label: "Good" };
  if (value >= 6) return { tier: "warning", label: "Fair" };
  if (value >= 4) return { tier: "serious", label: "Poor" };
  return { tier: "critical", label: "Critical" };
}

// Status-tier variant of meterCellHTML, for the one column/number that
// should draw the eye first (the composite Average) -- the fill color
// carries severity instead of the neutral blue sequential ramp the
// per-factor columns use. The dot doubles as the "icon" pairing the status
// color with a text label (via its title tooltip), since color must never
// carry meaning alone.
function statusMeterCellHTML(value, max = 10) {
  if (value === null || value === undefined) {
    return `<span class="na">—</span>`;
  }
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  const band = scoreBand(value);
  return `<div class="meter-cell">
    <span class="status-dot status-${band.tier}" title="${band.label}"></span>
    <div class="meter-track"><div class="meter-fill status-${band.tier}" style="width:${pct}%"></div></div>
    <div class="meter-value meter-value-strong">${value.toFixed(1)}</div>
  </div>`;
}
