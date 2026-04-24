const API_BASE = "http://localhost:5000";

document.getElementById("analyze-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  hideAll();

  const body = {
    lat:            parseFloat(document.getElementById("lat").value),
    lon:            parseFloat(document.getElementById("lon").value),
    property_value: parseFloat(document.getElementById("property_value").value) || undefined,
    current_premium: parseFloat(document.getElementById("current_premium").value) || undefined,
  };

  try {
    const res  = await fetch(`${API_BASE}/api/analyze`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(body),
    });
    const data = await res.json();

    if (!res.ok) {
      showError(data.error || "Unknown error");
      return;
    }

    renderResults(data);
  } catch (err) {
    showError("Could not reach the API. Is the backend running?");
  }
});

function renderResults(d) {
  const gap = d.pricing_gap;
  const severity = (gap?.severity || "").toLowerCase();

  const banner = document.getElementById("verdict-banner");
  if (gap?.verdict) {
    const sign = gap.gap_euros > 0 ? "+" : "";
    banner.textContent = `${gap.verdict} by ${sign}€${fmt(gap.gap_euros)} (${sign}${fmt(gap.gap_pct)}%) — ${gap.severity}`;
    banner.className = "verdict-banner " + (severity === "critical" || severity === "major" ? severity : "correct");
  } else {
    banner.textContent = `Risk Rating: ${d.risk_rating}`;
    banner.className = "verdict-banner";
  }

  document.getElementById("flood-prob").textContent   = `${d.flood_probability_pct.toFixed(1)}%`;
  document.getElementById("risk-rating").textContent  = d.risk_rating;
  document.getElementById("eal").textContent          = `€${fmt(d.expected_annual_loss)}`;
  document.getElementById("rec-premium").textContent  = `€${fmt(d.recommended_premium)}`;

  const barsDiv = document.getElementById("risk-bars");
  barsDiv.innerHTML = "";
  for (const [label, pct] of Object.entries(d.risk_breakdown || {})) {
    barsDiv.innerHTML += `
      <div class="bar-row">
        <span class="bar-label">${label}</span>
        <div class="bar-track"><div class="bar-fill" style="width:${pct}%"></div></div>
        <span class="bar-pct">${pct.toFixed(1)}%</span>
      </div>`;
  }

  document.getElementById("results").hidden = false;
}

function fmt(n) {
  if (n === null || n === undefined) return "—";
  return Math.round(n).toLocaleString("de-DE");
}

function showError(msg) {
  document.getElementById("error-message").textContent = msg;
  document.getElementById("error-panel").hidden = false;
}

function hideAll() {
  document.getElementById("results").hidden    = true;
  document.getElementById("error-panel").hidden = true;
}
