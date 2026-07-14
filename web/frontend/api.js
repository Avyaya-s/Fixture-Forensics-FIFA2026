async function fetchJSON(url) {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`${url} -> HTTP ${res.status}`);
  }
  return res.json();
}

function getTooltip() {
  let el = document.querySelector(".viz-tooltip");
  if (!el) {
    el = document.createElement("div");
    el.className = "viz-tooltip";
    document.body.appendChild(el);
  }
  return el;
}

function showTooltip(evt, html) {
  const el = getTooltip();
  el.innerHTML = html;
  el.classList.add("visible");
  positionTooltip(evt);
}

function positionTooltip(evt) {
  const el = getTooltip();
  const pad = 14;
  let x = evt.clientX + pad;
  let y = evt.clientY + pad;
  const rect = el.getBoundingClientRect();
  if (x + rect.width > window.innerWidth) x = evt.clientX - rect.width - pad;
  if (y + rect.height > window.innerHeight) y = evt.clientY - rect.height - pad;
  el.style.left = `${x}px`;
  el.style.top = `${y}px`;
}

function hideTooltip() {
  getTooltip().classList.remove("visible");
}
