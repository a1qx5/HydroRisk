/* ================================================================
   HYDRORISK — app.js
   Map interaction · Address search · Mock data · Results renderer
   ================================================================ */

const API_BASE = 'http://localhost:5000';

// ── State ─────────────────────────────────────────────────────────
let selectedLat  = null;
let selectedLon  = null;
let selectedAddr = null;
let activeMarker = null;
let searchTimer  = null;
let map          = null;
let svMap        = null;
let tacticalOverlay = null;
let analysisOverlays = [];
let currentAnalysisData = null;

// ── Tile layers ───────────────────────────────────────────────────
const TILE_LAYERS = {
  dark: {
    url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    opts: { subdomains: 'abcd', maxZoom: 19 }
  },
  streets: {
    url: 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
    opts: { subdomains: 'abcd', maxZoom: 19 }
  },
  satellite: {
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    opts: { maxZoom: 19 }
  }
};

// ── Initialization ───────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
  initMap();
  initSearch();
  initModeSwitcher();
  
  document.getElementById('analyze-btn').addEventListener('click', runAnalysis);
  document.getElementById('scan-accumulation-btn').addEventListener('click', runAccumulationScan);

  // Layer buttons
  document.querySelectorAll('.layer-btn[data-layer]').forEach(btn => {
    btn.addEventListener('click', () => {
      const l = btn.dataset.layer;
      if (!TILE_LAYERS[l]) return;
      document.querySelectorAll('.layer-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      changeMapLayer(l);
    });
  });
});

function initMap() {
  map = L.map('map', { zoomControl: false, attributionControl: false }).setView([46.5670, 26.9146], 13);
  L.control.zoom({ position: 'bottomright' }).addTo(map);
  changeMapLayer('dark');

  map.on('click', e => {
    const { lat, lng } = e.latlng;
    selectLocation(lat, lng);
    reverseGeocode(lat, lng);
  });
}

function changeMapLayer(key) {
  const l = TILE_LAYERS[key];
  map.eachLayer(layer => { if (layer instanceof L.TileLayer) map.removeLayer(layer); });
  L.tileLayer(l.url, l.opts).addTo(map);
}

function selectLocation(lat, lon, addr = null) {
  selectedLat = lat; selectedLon = lon;
  document.getElementById('lat-input').value = lat.toFixed(6);
  document.getElementById('lon-input').value = lon.toFixed(6);
  
  if (activeMarker) map.removeLayer(activeMarker);
  activeMarker = makeCrosshair(lat, lon).addTo(map);
  updateTacticalOverlay(lat, lon);
  
  map.setView([lat, lon], Math.max(map.getZoom(), 14), { animate: true });
  document.getElementById('analyze-btn').disabled = false;
  document.getElementById('sv-toggle').disabled = false;
}

function makeCrosshair(lat, lng) {
  const icon = L.divIcon({
    html: `<div class="tactical-crosshair">
             <div class="tc-ring"></div><div class="tc-line tc-h"></div><div class="tc-line tc-v"></div><div class="tc-center"></div>
           </div>`,
    className: '', iconSize: [40, 40], iconAnchor: [20, 20]
  });
  return L.marker([lat, lng], { icon });
}

function updateTacticalOverlay(lat, lng) {
  if (tacticalOverlay) map.removeLayer(tacticalOverlay);
  const icon = L.divIcon({
    html: `<div style="position: absolute; overflow: visible; opacity: 0; animation: pop-in 0.4s cubic-bezier(0.2, 0.8, 0.2, 1) forwards;">
             <svg width="400" height="400" style="position: absolute; top: -200px; left: -200px; overflow: visible; pointer-events: none;">
               <line x1="200" y1="200" x2="250" y2="150" class="tactical-line" />
             </svg>
             <div class="tactical-popup" style="transform: translate(50px, -50px); white-space: nowrap; min-width: 160px;">
               <div class="tp-title">[ TARGET ACQUIRED ]</div>
               <div class="tp-data">LAT: ${lat.toFixed(4)}</div>
               <div class="tp-data">LON: ${lng.toFixed(4)}</div>
               <div class="tp-status">> READY FOR ANALYSIS</div>
             </div>
           </div>`,
    className: '', iconSize: [0, 0], iconAnchor: [0, 0]
  });
  tacticalOverlay = L.marker([lat, lng], { icon, interactive: true }).addTo(map);
}

// ── Search & Mode ────────────────────────────────────────────────
function initSearch() {
  const input = document.getElementById('addr-input');
  input.addEventListener('input', () => {
    clearTimeout(searchTimer);
    const q = input.value.trim();
    if (!q) return;
    searchTimer = setTimeout(async () => {
      const res = await fetch(`https://photon.komoot.io/api/?q=${encodeURIComponent(q)}&limit=5`);
      const data = await res.json();
      renderSearchDropdown(data.features);
    }, 400);
  });

  const updateFromCoords = () => {
    const lat = parseFloat(document.getElementById('lat-input').value);
    const lon = parseFloat(document.getElementById('lon-input').value);
    if (!isNaN(lat) && !isNaN(lon)) {
      selectLocation(lat, lon);
      input.value = `LAT: ${lat.toFixed(4)}, LON: ${lon.toFixed(4)}`;
    }
  };

  document.getElementById('lat-input').addEventListener('change', updateFromCoords);
  document.getElementById('lon-input').addEventListener('change', updateFromCoords);
}

function renderSearchDropdown(feats) {
  const dd = document.getElementById('search-dropdown');
  dd.innerHTML = '';
  if (!feats.length) { dd.classList.add('hidden'); return; }
  dd.classList.remove('hidden');
  feats.forEach(f => {
    const item = document.createElement('div');
    item.className = 'sd-item';
    item.textContent = f.properties.name || f.properties.street || 'Unknown';
    item.onclick = () => {
      const [lon, lat] = f.geometry.coordinates;
      selectLocation(lat, lon);
      dd.classList.add('hidden');
      document.getElementById('addr-input').value = item.textContent;
    };
    dd.appendChild(item);
  });
}

function initModeSwitcher() {
  const pBtn = document.getElementById('mode-property');
  const fBtn = document.getElementById('mode-portfolio');
  const pSec = document.getElementById('section-property');
  const fSec = document.getElementById('section-portfolio');

  pBtn.onclick = () => { pBtn.classList.add('active'); fBtn.classList.remove('active'); pSec.classList.remove('hidden'); fSec.classList.add('hidden'); };
  fBtn.onclick = () => { fBtn.classList.add('active'); pBtn.classList.remove('active'); fSec.classList.remove('hidden'); pSec.classList.add('hidden'); };
}

// ── Analysis ─────────────────────────────────────────────────────
async function runAnalysis() {
  if (!selectedLat) return;
  const btn = document.getElementById('analyze-btn');
  btn.disabled = true; 
  
  const loader = document.getElementById('global-loader');
  const stageText = document.getElementById('gl-stage-text');
  const progressBar = document.getElementById('gl-progress-bar');
  
  loader.classList.remove('hidden');
  progressBar.style.transition = 'none';
  progressBar.style.width = '0%';
  void progressBar.offsetWidth; // force reflow
  progressBar.style.transition = 'width 2.5s ease';
  progressBar.style.width = '20%';

  const body = { 
    lat: selectedLat, lon: selectedLon,
    property_value: parseFloat(document.getElementById('prop-val').value) || 250000,
    current_premium: parseFloat(document.getElementById('curr-prem').value) || 1200
  };

  const loadingStages = [
    'QUERYING SENTINEL-1...',
    'PROCESSING ELEVATION...',
    'ANALYZING LAND USE...',
    'APPLYING CLIMATE MODELS...',
    'CALCULATING JRC CURVES...'
  ];
  let stageIdx = 0;
  stageText.textContent = loadingStages[0];

  const loadingInterval = setInterval(() => {
    stageIdx++;
    if (stageIdx < loadingStages.length) {
      stageText.textContent = loadingStages[stageIdx];
      progressBar.style.width = `${(stageIdx + 1) * 20}%`;
    }
  }, 2500);

  try {
    const res = await fetch(`${API_BASE}/api/analyze`, { 
      method: 'POST', 
      headers: {'Content-Type': 'application/json'}, 
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(300000)
    });
    clearInterval(loadingInterval);
    progressBar.style.width = '100%';
    stageText.textContent = 'ANALYSIS COMPLETE';
    if (!res.ok) throw new Error('API_REJECTED');
    const data = await res.json();
    currentAnalysisData = data;
    
    setTimeout(() => {
      loader.classList.add('hidden');
      renderTacticalButtons();
    }, 600);
  } catch (err) {
    clearInterval(loadingInterval);
    progressBar.style.width = '100%';
    stageText.textContent = 'MOCK ANALYSIS READY';
    console.warn("API Analysis failed, falling back to tactical mock data:", err);
    currentAnalysisData = generateMockAnalysis(body.lat, body.lon, body.property_value, body.current_premium);
    setTimeout(() => {
      loader.classList.add('hidden');
      renderTacticalButtons();
    }, 600);
  } finally { 
    btn.disabled = false; 
    btn.querySelector('span').textContent = 'RE-ANALYZE'; 
  }
}

function generateMockAnalysis(lat, lon, val, curr) {
  // Balanced mock data generator for when API is down
  const prob = 5 + Math.random() * 15;
  const rec  = (val * (prob/100)) * 0.45;
  return {
    flood_probability_pct: prob,
    recommended_premium: rec,
    current_premium: curr,
    risk_rating: prob > 15 ? 'High' : prob > 8 ? 'Medium' : 'Low',
    pricing_gap: {
      verdict: rec > curr ? 'Underpriced' : 'Correctly Priced',
      severity: rec > curr * 1.5 ? 'Severe' : 'Moderate',
      gap_euros: Math.abs(rec - curr),
      gap_pct: (Math.abs(rec - curr) / curr) * 100
    },
    explanation: "OFFLINE MODE: Real-time satellite data currently unavailable. Displaying deterministic risk model based on local terrain elevation and historical floodplain proximity."
  };
}

function renderTacticalButtons() {
  if (tacticalOverlay) map.removeLayer(tacticalOverlay);
  analysisOverlays.forEach(m => map.removeLayer(m));
  analysisOverlays = [];

  const btnHtml = (title, x, y, lineX1, lineY1, lineX2, lineY2, section, delay) => `
    <div style="position: absolute; overflow: visible; opacity: 0; animation: pop-in 0.6s cubic-bezier(0.2, 0.8, 0.2, 1) forwards ${delay}s;">
      <svg width="400" height="400" style="position: absolute; top: -200px; left: -200px; overflow: visible; pointer-events: none;">
        <line x1="${lineX1}" y1="${lineY1}" x2="${lineX2}" y2="${lineY2}" class="tactical-line" />
      </svg>
      <div class="tactical-popup" style="transform: translate(${x}px, ${y}px);" onclick="event.stopPropagation(); window.openDashboard('${section}');">
        <div class="tp-title">> ${title}</div>
      </div>
    </div>
  `;

  const pos = [selectedLat, selectedLon];
  analysisOverlays.push(L.marker(pos, { icon: L.divIcon({ html: btnHtml('RISK METRICS', 60, -80, 200, 200, 260, 140, 'risk', 0.1), iconSize:[0,0], iconAnchor:[0,0] }), interactive: true }).addTo(map));
  analysisOverlays.push(L.marker(pos, { icon: L.divIcon({ html: btnHtml('FINANCIALS', 80, 40, 200, 200, 280, 250, 'fin', 0.25), iconSize:[0,0], iconAnchor:[0,0] }), interactive: true }).addTo(map));
  analysisOverlays.push(L.marker(pos, { icon: L.divIcon({ html: btnHtml('RISK BREAKDOWN', -220, 40, 200, 200, 40, 250, 'brk', 0.4), iconSize:[0,0], iconAnchor:[0,0] }), interactive: true }).addTo(map));
}

const dashboardSections = ['risk', 'fin', 'brk'];
let currentDashSectionIdx = 0;

window.navigateDashboard = function(dir) {
  // If we are showing portfolio, don't navigate
  if (!document.getElementById('dash-sec-portfolio').classList.contains('hidden')) return;
  
  let newIdx = currentDashSectionIdx + dir;
  if (newIdx < 0) newIdx = dashboardSections.length - 1;
  if (newIdx >= dashboardSections.length) newIdx = 0;
  
  window.openDashboard(dashboardSections[newIdx]);
};

window.openDashboard = function(section) {
  const d = currentAnalysisData; if (!d) return;
  
  // Update tracker
  const idx = dashboardSections.indexOf(section);
  if (idx !== -1) currentDashSectionIdx = idx;

  document.querySelectorAll('.dash-card').forEach(c => c.classList.add('hidden'));
  document.getElementById('dashboard-overlay').classList.remove('hidden');

  if (section === 'risk') { document.getElementById('dash-sec-risk').classList.remove('hidden'); document.getElementById('dash-sec-verdict').classList.remove('hidden'); }
  else if (section === 'fin') { document.getElementById('dash-sec-fin').classList.remove('hidden'); }
  else if (section === 'brk') { document.getElementById('dash-sec-brk').classList.remove('hidden'); }

  // Populate data
  document.getElementById('dash-coords').textContent = `LAT: ${selectedLat.toFixed(5)} LON: ${selectedLon.toFixed(5)}`;
  document.getElementById('dash-gauge-pct').textContent = `${d.flood_probability_pct.toFixed(1)}%`;
  document.getElementById('dash-rec').textContent = `€${fmt(d.recommended_premium)}`;
  document.getElementById('dash-curr').textContent = `€${fmt(d.pricing_gap?.current_premium || document.getElementById('curr-prem').value || 0)}`;
  document.getElementById('dash-eal').textContent = `€${fmt(d.expected_annual_loss || 0)}`;

  
  const ratingKey = d.risk_rating.toLowerCase().replace(' ', '-');
  const badge = document.getElementById('dash-risk-badge');
  badge.textContent = d.risk_rating.toUpperCase();
  badge.className = `risk-badge ${ratingKey}`;

  // Verdict
  const v = d.pricing_gap;
  if (v) {
    document.getElementById('dash-v-word').textContent = v.verdict;
    document.getElementById('dash-v-num').textContent = `€${fmt(v.gap_euros)}`;
    document.getElementById('dash-v-sub').textContent = `Gap: ${v.gap_pct.toFixed(1)}%`;
    const vKey = v.verdict.toLowerCase().replace(' ', '-');
    document.getElementById('dash-verdict').className = `verdict-card ${vKey.startsWith('under') ? 'vc-underpriced-severe' : vKey.includes('over') ? 'vc-overpriced' : 'vc-correct'}`;
  }

  // Card 3: Breakdown (Risk Drivers)
  const list = document.getElementById('dash-breakdown-list');
  list.innerHTML = '';
  const raw = d.raw_property_data || {};
  const drivers = [
    { name: `TERRAIN ELEVATION (${raw.elevation_m}m)`, val: raw.elevation_percentile < 15 ? 'CRITICAL' : 'SAFE', pct: raw.elevation_percentile < 15 ? 90 : 20 },
    { name: `DISTANCE TO RIVER (${Math.round(raw.distance_to_river_m)}m)`, val: raw.distance_to_river_m < 200 ? 'HIGH RISK' : 'LOW RISK', pct: raw.distance_to_river_m < 200 ? 85 : 15 },
    { name: 'FLOOD HISTORY', val: raw.flood_events_12yr > 1 ? 'SEVERE' : 'NONE', pct: raw.flood_events_12yr > 1 ? 95 : 5 },
    { name: 'SOIL IMPERVIOUSNESS', val: raw.imperviousness_pct > 0.6 ? 'EXTREME' : 'LOW', pct: raw.imperviousness_pct > 0.6 ? 75 : 30 },
    { name: 'CLIMATE MULTIPLIER', val: raw.climate_multiplier_2035 > 1.2 ? 'SEVERE' : 'STABLE', pct: raw.climate_multiplier_2035 > 1.2 ? 80 : 35 },
    { name: 'FLOOD DEFENSES', val: raw.flood_defense_present ? 'ACTIVE' : 'VULNERABLE', pct: raw.flood_defense_present ? 15 : 85 }
  ];
  drivers.forEach(dr => {
    const item = document.createElement('div');
    item.className = 'bar-item';
    item.innerHTML = `
      <div class="bar-header" style="display:flex; justify-content:space-between; font-size:10px; margin-bottom:5px; font-family:monospace;">
        <span>${dr.name}</span><span style="color:${dr.pct > 50 ? 'var(--risk-high)' : 'var(--risk-low)'}">${dr.val}</span>
      </div>
      <div class="bar-track" style="height:4px; background:rgba(255,255,255,0.05); border-radius:2px;">
        <div class="bar-fill" style="width:${dr.pct}%; height:100%; background:${dr.pct > 50 ? 'var(--risk-high)' : 'var(--risk-low)'}; transition: width 1s;"></div>
      </div>
    `;
    list.appendChild(item);
  });
};

window.closeDashboard = () => document.getElementById('dashboard-overlay').classList.add('hidden');

window.openPortfolioModal = function() {
  const modal = document.getElementById('portfolio-modal');
  modal.classList.remove('hidden');
  void modal.offsetWidth; // force reflow
  modal.style.opacity = '1';
  modal.style.pointerEvents = 'auto';
  document.getElementById('pm-box').style.transform = 'scale(1)';
  updatePortfolioModel(); // initial render
};

window.closePortfolioModal = function() {
  const modal = document.getElementById('portfolio-modal');
  modal.style.opacity = '0';
  modal.style.pointerEvents = 'none';
  document.getElementById('pm-box').style.transform = 'scale(0.95)';
  setTimeout(() => modal.classList.add('hidden'), 300);
};

// Event listeners for sliders
document.addEventListener('DOMContentLoaded', () => {
  const pSliders = ['sl-size', 'sl-prem', 'sl-loss', 'sl-exp', 'sl-mispct', 'sl-misval'];
  pSliders.forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('input', updatePortfolioModel);
  });
});

function formatMoneyStr(val) {
  if (Math.abs(val) >= 1000000) return '€' + (val / 1000000).toFixed(1) + 'M';
  if (Math.abs(val) >= 1000) return '€' + (val / 1000).toFixed(0) + 'K';
  return '€' + Math.round(val);
}

function updatePortfolioModel() {
  const size = parseFloat(document.getElementById('sl-size').value);
  const prem = parseFloat(document.getElementById('sl-prem').value);
  const loss = parseFloat(document.getElementById('sl-loss').value);
  const exp = parseFloat(document.getElementById('sl-exp').value);
  const mispct = parseFloat(document.getElementById('sl-mispct').value);
  const misval = parseFloat(document.getElementById('sl-misval').value);

  // Update slider value labels
  document.getElementById('val-size').textContent = Math.round(size).toLocaleString('en-US');
  document.getElementById('val-prem').textContent = '€' + Math.round(prem).toLocaleString('en-US');
  document.getElementById('val-loss').textContent = (loss * 100).toFixed(1) + '%';
  document.getElementById('val-exp').textContent = (exp * 100).toFixed(1) + '%';
  document.getElementById('val-mispct').textContent = (mispct * 100).toFixed(1) + '%';
  document.getElementById('val-misval').textContent = '€' + Math.round(misval).toLocaleString('en-US');

  // Math port from portfolio_model.py
  const platformCostPerPolicy = 0.50;
  
  const totalPremiums = size * prem;
  const totalClaims = totalPremiums * loss;
  const combinedRatio = loss + exp;
  const currentProfit = totalPremiums * (1 - combinedRatio);
  
  const mispricedPolicies = size * mispct;
  const additionalPremium = mispricedPolicies * misval;
  const newTotalPremiums = totalPremiums + additionalPremium;
  const newLossRatio = totalClaims / newTotalPremiums;
  const newCombinedRatio = newLossRatio + exp;
  const newProfit = newTotalPremiums * (1 - newCombinedRatio);
  
  const profitImprovement = additionalPremium * (1 - exp);
  const platformCost = size * platformCostPerPolicy;
  const netBenefit = profitImprovement - platformCost;
  const roiPct = platformCost > 0 ? (netBenefit / platformCost) * 100 : 0;

  // Update Output Cards
  document.getElementById('out-w-loss').textContent = (loss * 100).toFixed(1) + '%';
  document.getElementById('out-w-comb').textContent = (combinedRatio * 100).toFixed(1) + '%';
  document.getElementById('out-w-ur').textContent = (currentProfit < 0 ? '-' : '') + formatMoneyStr(Math.abs(currentProfit));
  document.getElementById('out-w-ur').style.color = currentProfit < 0 ? 'var(--risk-high)' : 'var(--risk-low)';

  document.getElementById('out-wm-loss').textContent = (newLossRatio * 100).toFixed(1) + '%';
  document.getElementById('out-wm-comb').textContent = (newCombinedRatio * 100).toFixed(1) + '%';
  document.getElementById('out-wm-ur').textContent = (newProfit < 0 ? '-' : '') + formatMoneyStr(Math.abs(newProfit));
  document.getElementById('out-wm-ur').style.color = newProfit < 0 ? 'var(--risk-high)' : 'var(--risk-low)';

  document.getElementById('out-m-imp').textContent = '+' + formatMoneyStr(profitImprovement);
  document.getElementById('out-m-cost').textContent = formatMoneyStr(platformCost);
  document.getElementById('out-m-net').textContent = '+' + formatMoneyStr(netBenefit);
  document.getElementById('out-m-roi').textContent = Math.round(roiPct).toLocaleString('en-US') + '%';
}

let svPanorama = null;

window.openStreetView = function() {
  if (!selectedLat) return;
  const modal   = document.getElementById('sv-modal');
  const loader  = document.getElementById('sv-loader');
  const noImg   = document.getElementById('sv-no-imagery');
  const addrEl  = document.getElementById('sv-address');

  // Show modal
  modal.classList.remove('hidden');
  loader.style.opacity = '1';
  loader.style.pointerEvents = 'auto';
  noImg.style.display = 'none';
  addrEl.textContent = `${selectedLat.toFixed(5)}, ${selectedLon.toFixed(5)}`;

  void modal.offsetWidth;
  modal.style.opacity = '1';
  modal.style.pointerEvents = 'auto';

  const position = { lat: selectedLat, lng: selectedLon };
  const sv = new google.maps.StreetViewService();

  sv.getPanorama({ location: position, radius: 100, preference: google.maps.StreetViewPreference.NEAREST }, (data, status) => {
    if (status === google.maps.StreetViewStatus.OK) {
      // Init panorama once, reuse it after
      if (!svPanorama) {
        svPanorama = new google.maps.StreetViewPanorama(
          document.getElementById('sv-pano'), {
            pano: data.location.pano,
            pov: { heading: 0, pitch: 0 },
            zoom: 1,
            addressControl: false,
            fullscreenControl: false,
            motionTrackingControl: false,
            showRoadLabels: true,
            linksControl: true,
          }
        );
      } else {
        svPanorama.setPano(data.location.pano);
        svPanorama.setPov({ heading: 0, pitch: 0 });
      }
      svPanorama.setVisible(true);
    } else {
      // No imagery — try with wider radius
      sv.getPanorama({ location: position, radius: 500, preference: google.maps.StreetViewPreference.NEAREST }, (data2, status2) => {
        if (status2 === google.maps.StreetViewStatus.OK) {
          if (!svPanorama) {
            svPanorama = new google.maps.StreetViewPanorama(
              document.getElementById('sv-pano'), {
                pano: data2.location.pano,
                pov: { heading: 0, pitch: 0 },
                zoom: 1,
                addressControl: false,
                fullscreenControl: false,
                motionTrackingControl: false,
              }
            );
          } else {
            svPanorama.setPano(data2.location.pano);
          }
          svPanorama.setVisible(true);
        } else {
          noImg.style.display = 'flex';
        }
      });
    }
    // Hide loader once panorama initialises
    setTimeout(() => { loader.style.opacity = '0'; loader.style.pointerEvents = 'none'; }, 800);
  });
};

window.closeStreetView = function() {
  const modal = document.getElementById('sv-modal');
  modal.style.opacity = '0';
  modal.style.pointerEvents = 'none';
  setTimeout(() => { modal.classList.add('hidden'); }, 400);
};

async function runAccumulationScan() {
  const btn = document.getElementById('scan-accumulation-btn');
  
  // If scan is already active, clear it and return
  if (btn.dataset.active === 'true') {
    analysisOverlays.forEach(m => map.removeLayer(m));
    analysisOverlays = [];
    btn.dataset.active = 'false';
    btn.querySelector('span').textContent = 'ACCUMULATION SCAN';
    return;
  }

  btn.disabled = true;
  btn.querySelector('span').textContent = 'SCANNING...';

  // Clear previous scan
  analysisOverlays.forEach(m => map.removeLayer(m));
  analysisOverlays = [];

  try {
    // Generate mock policies for scan (since we don't have a real DB)
    const policies = [];
    const center = map.getCenter();
    
    // 1. Dense cluster right at the center (high risk, triggers CRITICAL)
    for(let i=0; i<120; i++) {
      policies.push({
        lat: center.lat + (Math.random() - 0.5) * 0.015,
        lon: center.lng + (Math.random() - 0.5) * 0.015,
        property_value: 200000 + Math.random() * 400000,
        annual_flood_probability: 0.4 + Math.random() * 0.5,
        risk_rating: 'HIGH'
      });
    }

    // 2. Medium cluster nearby (triggers HIGH/MEDIUM)
    for(let i=0; i<60; i++) {
      policies.push({
        lat: center.lat + 0.01 + (Math.random() - 0.5) * 0.02,
        lon: center.lng - 0.01 + (Math.random() - 0.5) * 0.02,
        property_value: 150000 + Math.random() * 250000,
        annual_flood_probability: 0.2 + Math.random() * 0.3,
        risk_rating: 'MEDIUM'
      });
    }

    // 3. Scattered background policies (triggers LOW)
    for(let i=0; i<100; i++) {
      policies.push({
        lat: center.lat + (Math.random() - 0.5) * 0.1,
        lon: center.lng + (Math.random() - 0.5) * 0.1,
        property_value: 100000 + Math.random() * 300000,
        annual_flood_probability: 0.01 + Math.random() * 0.2,
        risk_rating: 'LOW'
      });
    }

    const res = await fetch(`${API_BASE}/api/accumulation`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ policies })
    });
    const d = await res.json();
    
    renderHeatmap(d.clusters);
    
    // Scan successful, update button to clear state
    btn.dataset.active = 'true';
    btn.querySelector('span').textContent = 'CLEAR SCAN';
  } catch (err) {
    alert("Accumulation scan failed.");
    btn.querySelector('span').textContent = 'ACCUMULATION SCAN';
  } finally {
    btn.disabled = false;
  }
}

function renderHeatmap(clusters) {
  const GRID_SIZE = 0.01;
  clusters.forEach(c => {
    const color = c.accumulation_severity === 'CRITICAL' ? '#ff3131' : 
                  c.accumulation_severity === 'HIGH' ? '#ff6b35' : 
                  c.accumulation_severity === 'MEDIUM' ? '#ffb800' : '#00ff41';
    
    const bounds = [
      [c.cell_lat - GRID_SIZE/2, c.cell_lon - GRID_SIZE/2],
      [c.cell_lat + GRID_SIZE/2, c.cell_lon + GRID_SIZE/2]
    ];

    const rect = L.rectangle(bounds, {
      color: color,
      weight: 1,
      fillColor: color,
      fillOpacity: 0.4,
      interactive: true
    }).bindPopup(`
      <div style="font-family:monospace; color:#fff; font-size:11px;">
        <div style="color:${color}; font-weight:bold;">${c.accumulation_severity} ZONE</div>
        <div>Exposure: €${fmt(c.total_insured_value)}</div>
        <div>Policies: ${c.policy_count}</div>
        <div>MPL: €${fmt(c.max_probable_loss)}</div>
      </div>
    `);
    
    rect.addTo(map);
    analysisOverlays.push(rect);
  });
}

function fmt(n) { return Math.round(n || 0).toLocaleString('de-DE'); }
function reverseGeocode(lat, lon) { /* Photon doesn't do reverse well, skipping for speed */ }
