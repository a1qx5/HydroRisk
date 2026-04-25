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

// ── DOM refs ──────────────────────────────────────────────────────
const addrInput     = () => document.getElementById('addr-input');
const latInput      = () => document.getElementById('lat-input');
const lonInput      = () => document.getElementById('lon-input');
const propValInput  = () => document.getElementById('prop-val');
const currPremInput = () => document.getElementById('curr-prem');
const analyzeBtn    = () => document.getElementById('analyze-btn');
const analyzeBtnLbl = () => document.getElementById('analyze-btn-label');
const searchDD      = () => document.getElementById('search-dropdown');
const mapHint       = () => document.getElementById('map-hint');

// ── Tile layer definitions ────────────────────────────────────────
const TILE_LAYERS = {
  dark: {
    url:   'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    opts:  { subdomains: 'abcd', maxZoom: 19,
             attribution: '© <a href="https://www.openstreetmap.org/copyright">OSM</a> contributors © <a href="https://carto.com">CARTO</a>' },
    label: 'DARK',
  },
  streets: {
    url:   'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
    opts:  { subdomains: 'abcd', maxZoom: 19,
             attribution: '© <a href="https://www.openstreetmap.org/copyright">OSM</a> contributors © <a href="https://carto.com">CARTO</a>' },
    label: 'STREETS',
  },
  satellite: {
    url:   'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    opts:  { maxZoom: 19,
             attribution: '© <a href="https://www.esri.com">Esri</a>, Maxar, Earthstar Geographics' },
    label: 'SATELLITE',
    // labels overlay on top of satellite
    labelsUrl:  'https://{s}.basemaps.cartocdn.com/dark_only_labels/{z}/{x}/{y}{r}.png',
    labelsOpts: { subdomains: 'abcd', maxZoom: 19, pane: 'shadowPane' },
  },
};

let activeLayer      = null;
let activeLabels     = null;
let activeLayerName  = 'dark';

// ── Map init ──────────────────────────────────────────────────────
function initMap() {
  map = L.map('map', {
    center: [45.9432, 24.9668], // Romania
    zoom: 7,
    zoomControl: true,
  });

  setLayer('dark');
  map.on('click', (e) => onMapClick(e.latlng.lat, e.latlng.lng));
}

function setLayer(name) {
  const def = TILE_LAYERS[name];
  if (!def) return;

  if (activeLayer)  { map.removeLayer(activeLayer);  activeLayer  = null; }
  if (activeLabels) { map.removeLayer(activeLabels); activeLabels = null; }

  activeLayer = L.tileLayer(def.url, def.opts).addTo(map);

  if (def.labelsUrl) {
    activeLabels = L.tileLayer(def.labelsUrl, def.labelsOpts).addTo(map);
  }

  activeLayerName = name;

  // Update button states
  document.querySelectorAll('.mc-btn[data-layer]').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.layer === name);
  });
}

function initLayerControls() {
  document.querySelectorAll('.mc-btn[data-layer]').forEach(btn => {
    btn.addEventListener('click', () => setLayer(btn.dataset.layer));
  });
}

function makeMarker(lat, lng) {
  const icon = L.divIcon({
    html: `<div class="hydro-marker">
             <div class="hm-ring"></div>
             <div class="hm-ring-2"></div>
             <div class="hm-dot"></div>
           </div>`,
    className: '',
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  });
  return L.marker([lat, lng], { icon });
}

// ── Location selection ────────────────────────────────────────────
function selectLocation(lat, lon, address) {
  selectedLat  = lat;
  selectedLon  = lon;
  selectedAddr = address || null;

  latInput().value = lat.toFixed(6);
  lonInput().value = lon.toFixed(6);

  if (activeMarker) map.removeLayer(activeMarker);
  activeMarker = makeMarker(lat, lon).addTo(map);
  map.setView([lat, lon], Math.max(map.getZoom(), 14), { animate: true });

  mapHint().classList.add('hidden');
  analyzeBtn().disabled = false;
  analyzeBtnLbl().textContent = 'ANALYZE FLOOD RISK';
  document.getElementById('sv-toggle').disabled = false;
}

function onMapClick(lat, lon) {
  selectLocation(lat, lon, null);
  reverseGeocode(lat, lon);
}

// ── Geocoding (Photon — built for address autocomplete on OSM) ────
async function geocode(query) {
  const url = `https://photon.komoot.io/api/?q=${encodeURIComponent(query)}&limit=6&lang=en`;
  const res  = await fetch(url);
  if (!res.ok) return [];
  const data = await res.json();
  return data.features || [];
}

function photonLabel(f) {
  // Build a clean "Primary line / Secondary line" from Photon properties
  const p = f.properties;
  const primary = [
    p.name,
    p.housenumber ? `${p.street || ''} ${p.housenumber}`.trim() : p.street,
  ].filter(Boolean).join(', ') || p.city || p.county || 'Unknown';

  const secondary = [
    (!primary.includes(p.city) ? p.city : null),
    p.state,
    p.country,
  ].filter(Boolean).join(', ');

  return { primary, secondary };
}

async function reverseGeocode(lat, lon) {
  try {
    const url = `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json`;
    const res  = await fetch(url, { headers: { 'Accept-Language': 'en' } });
    if (!res.ok) return;
    const data = await res.json();
    selectedAddr = data.display_name || null;
    const el = document.getElementById('res-addr');
    if (el && selectedAddr) el.textContent = selectedAddr;
  } catch (_) { /* offline — skip */ }
}

function parseCoords(str) {
  const m = str.trim().match(/^(-?\d{1,3}(?:\.\d+)?)[,\s]+(-?\d{1,3}(?:\.\d+)?)$/);
  if (!m) return null;
  const lat = parseFloat(m[1]), lon = parseFloat(m[2]);
  if (lat < -90 || lat > 90 || lon < -180 || lon > 180) return null;
  return { lat, lon };
}

// ── Search box ────────────────────────────────────────────────────
function initSearch() {
  const input = addrInput();

  input.addEventListener('input', () => {
    clearTimeout(searchTimer);
    const q = input.value.trim();
    if (!q) { hideDropdown(); return; }

    const coords = parseCoords(q);
    if (coords) {
      hideDropdown();
      selectLocation(coords.lat, coords.lon, `${coords.lat}, ${coords.lon}`);
      return;
    }
    searchTimer = setTimeout(() => runSearch(q), 350);
  });

  input.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') hideDropdown();
  });

  document.addEventListener('click', (e) => {
    if (!e.target.closest('.search-wrap') && !e.target.closest('.search-dropdown')) {
      hideDropdown();
    }
  });
}

async function runSearch(query) {
  try {
    const results = await geocode(query);
    if (!results.length) { hideDropdown(); return; }
    showDropdown(results);
  } catch (_) { hideDropdown(); }
}

function showDropdown(features) {
  const dd   = searchDD();
  const rect = addrInput().getBoundingClientRect();
  dd.innerHTML = '';

  features.forEach((f) => {
    const [lon, lat] = f.geometry.coordinates; // Photon returns [lon, lat]
    const { primary, secondary } = photonLabel(f);
    const fullLabel = secondary ? `${primary}, ${secondary}` : primary;

    const item = document.createElement('div');
    item.className = 'sd-item';
    item.innerHTML = `<strong>${primary}</strong>${secondary ? `<br><span>${secondary}</span>` : ''}`;

    item.addEventListener('mousedown', (e) => {
      e.preventDefault(); // prevent input blur before selection
      addrInput().value = fullLabel;
      hideDropdown();
      selectLocation(lat, lon, fullLabel);
    });
    dd.appendChild(item);
  });

  dd.style.top   = `${rect.bottom + 4}px`;
  dd.style.left  = `${rect.left}px`;
  dd.style.width = `${rect.width}px`;
  dd.classList.remove('hidden');
}

function hideDropdown() {
  searchDD().classList.add('hidden');
}

// ── Coord inputs ──────────────────────────────────────────────────
function initCoordInputs() {
  const apply = () => {
    const lat = parseFloat(latInput().value);
    const lon = parseFloat(lonInput().value);
    if (!isNaN(lat) && !isNaN(lon) && lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180) {
      selectLocation(lat, lon, null);
      reverseGeocode(lat, lon);
    }
  };
  latInput().addEventListener('change', apply);
  lonInput().addEventListener('change', apply);
}

// ── Mock data generator ───────────────────────────────────────────
function seededRand(seed) {
  const x = Math.sin(seed) * 43758.5453;
  return x - Math.floor(x);
}

function jrcDamage(depth) {
  const curve = [[0.1,0.04],[0.3,0.13],[0.5,0.22],[0.75,0.33],[1.0,0.44],[1.5,0.59],[2.0,0.70],[3.0,0.83]];
  if (depth <= 0 || depth < curve[0][0]) return 0;
  if (depth >= curve[curve.length-1][0]) return 0.97;
  for (let i = 0; i < curve.length-1; i++) {
    const [d0,f0] = curve[i], [d1,f1] = curve[i+1];
    if (depth >= d0 && depth <= d1) return f0 + (depth-d0)/(d1-d0)*(f1-f0);
  }
  return 0.97;
}

function getMockData(lat, lon, propertyValue, currentPremium) {
  const r1 = seededRand(lat * 127.1 + lon * 311.7);
  const r2 = seededRand(lat * 269.5 + lon * 183.3);
  const r3 = seededRand(lat * 419.2 + lon * 93.7);

  // Romanian geography: flood risk bias
  let bias = r1 * 0.55;
  if (lat < 44.8)                                   bias += 0.28; // Danube plain
  if (lat < 46.5 && lon > 27)                       bias += 0.22; // Siret/Prut corridor
  if (lat > 45.5 && lon > 23 && lon < 26)           bias -= 0.28; // Carpathians
  if (lat > 47)                                      bias -= 0.12; // Northern hills
  if (lon > 29 && lat < 45.5)                       bias += 0.18; // Danube delta

  const prob     = Math.max(0.03, Math.min(0.93, bias));
  const probPct  = Math.round(prob * 1000) / 10;

  const rating =
    prob < 0.05 ? 'LOW' :
    prob < 0.15 ? 'MEDIUM' :
    prob < 0.35 ? 'HIGH' : 'VERY HIGH';

  const depth =
    prob < 0.05 ? 0.12 + r2 * 0.08 :
    prob < 0.15 ? 0.25 + r2 * 0.20 :
    prob < 0.35 ? 0.60 + r2 * 0.40 :
                  1.0  + r2 * 0.80;

  const propVal      = propertyValue || 200000;
  const dmgFrac      = jrcDamage(depth);
  const dmgPerEvent  = propVal * dmgFrac;
  const eal          = prob * dmgPerEvent;
  const recPrem      = eal / 0.65;

  // Risk breakdown (deterministic, sum to 100)
  const fh = 0.15 + r1 * 0.35;
  const tr = 0.12 + r2 * 0.30;
  const lu = 0.07 + r3 * 0.18;
  const cl = 0.07 + r1 * 0.08;
  const df = 0.02 + r2 * 0.04;
  const tot = fh + tr + lu + cl + df;
  const pct = (v) => Math.round(v / tot * 1000) / 10;

  const breakdown = {
    'Flood History': pct(fh),
    'Terrain':       pct(tr),
    'Land Use':      pct(lu),
    'Climate':       pct(cl),
    'Defenses':      pct(df),
  };
  // Correct rounding drift on largest component
  const sum  = Object.values(breakdown).reduce((a,b) => a+b, 0);
  const drift = Math.round((100 - sum) * 10) / 10;
  breakdown['Terrain'] = Math.round((breakdown['Terrain'] + drift) * 10) / 10;

  const topEntry = Object.entries(breakdown).sort((a,b) => b[1]-a[1])[0];

  // Pricing gap
  let pricingGap = null;
  if (currentPremium) {
    const gapE   = recPrem - currentPremium;
    const gapPct = currentPremium > 0 ? (gapE / currentPremium) * 100 : 0;
    const absP   = Math.abs(gapPct);
    const verdict  = absP <= 10 ? 'CORRECTLY PRICED' : gapE > 0 ? 'UNDERPRICED' : 'OVERPRICED';
    const severity = absP < 20 ? 'MINOR' : absP < 50 ? 'SIGNIFICANT' : absP < 100 ? 'MAJOR' : 'CRITICAL';
    const covPct   = eal > 0 ? (currentPremium / eal) * 100 : 0;
    pricingGap = {
      current_premium:     currentPremium,
      recommended_premium: Math.round(recPrem),
      gap_euros:           Math.round(gapE),
      gap_pct:             Math.round(gapPct * 10) / 10,
      verdict,
      severity,
      coverage_pct:        Math.round(covPct * 10) / 10,
    };
  }

  const explanation = buildExplanation(prob, rating, topEntry, eal, recPrem, currentPremium);

  return {
    flood_probability_pct:     probPct,
    risk_rating:               rating,
    recommended_premium:       Math.round(recPrem),
    expected_annual_loss:      Math.round(eal),
    expected_damage_per_event: Math.round(dmgPerEvent),
    damage_fraction_pct:       Math.round(dmgFrac * 1000) / 10,
    property_value_used:       propVal,
    property_value_source:     propertyValue ? 'PROVIDED' : 'DEFAULT_ESTIMATE',
    pricing_gap:               pricingGap,
    risk_breakdown:            breakdown,
    top_risk_driver:           { name: topEntry[0], pct: topEntry[1] },
    explanation,
    raw_probability_data: {
      expected_flood_depth_m: Math.round(depth * 100) / 100,
      confidence: prob > 0.3 ? 'HIGH' : prob > 0.1 ? 'MEDIUM' : 'LOW',
    },
    confidence: prob > 0.3 ? 'HIGH' : prob > 0.1 ? 'MEDIUM' : 'LOW',
    analysis_timestamp: new Date().toISOString(),
    _source: 'mock',
  };
}

function buildExplanation(prob, rating, topEntry, eal, recPrem, currPrem) {
  const parts = [
    `This property carries a ${(prob*100).toFixed(1)}% annual flood probability (${rating} risk).`,
    `The primary risk driver is ${topEntry[0]}, accounting for ${topEntry[1].toFixed(1)}% of the risk score.`,
    `Expected annual loss: €${fmt(eal)}.`,
  ];
  if (currPrem && eal > 0) {
    const cov = (currPrem / eal * 100).toFixed(1);
    const gap = recPrem - currPrem;
    if (gap > 0) {
      parts.push(`The current premium covers only ${cov}% of expected annual losses — underpriced by €${fmt(gap)}.`);
    } else {
      parts.push(`The recommended premium (€${fmt(recPrem)}) is below the current premium — this property may be overpriced.`);
    }
  }
  return parts.join(' ');
}

// ── API call with mock fallback ───────────────────────────────────
async function fetchAnalysis(lat, lon, propVal, currPrem) {
  try {
    const body = { lat, lon };
    if (propVal)  body.property_value  = propVal;
    if (currPrem) body.current_premium = currPrem;

    const res = await fetch(`${API_BASE}/api/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(12000),
    });
    if (!res.ok) throw new Error('API error');
    const data = await res.json();
    data._source = 'api';
    return data;
  } catch (_) {
    return getMockData(lat, lon, propVal, currPrem);
  }
}

// ── Analyze flow ──────────────────────────────────────────────────
const LOADING_STEPS = [
  'Querying Sentinel-1 archive…',
  'Processing terrain elevation…',
  'Applying climate projections…',
  'Calculating JRC damage curves…',
  'Computing premium…',
];

async function runAnalysis() {
  if (!selectedLat) return;
  analyzeBtn().disabled = true;
  analyzeBtnLbl().textContent = 'ANALYZING…';

  showState('loading');

  const stepEl = document.getElementById('loading-step');
  let stepIdx  = 0;
  const stepTimer = setInterval(() => {
    stepIdx = (stepIdx + 1) % LOADING_STEPS.length;
    stepEl.style.opacity = 0;
    setTimeout(() => {
      stepEl.textContent  = LOADING_STEPS[stepIdx];
      stepEl.style.opacity = 1;
    }, 200);
  }, 900);

  // Minimum display time so the loading state is visible
  const [data] = await Promise.all([
    fetchAnalysis(
      selectedLat,
      selectedLon,
      parseFloat(propValInput().value) || null,
      parseFloat(currPremInput().value) || null,
    ),
    new Promise(r => setTimeout(r, 1600)),
  ]);

  clearInterval(stepTimer);

  analyzeBtn().disabled = false;
  analyzeBtnLbl().textContent = 'RE-ANALYZE';

  renderResults(data);
  showState('results');
}

// ── State management ──────────────────────────────────────────────
function showState(state) {
  ['empty','loading','results'].forEach(s => {
    const el = document.getElementById(`state-${s}`);
    if (!el) return;
    el.classList.toggle('hidden', s !== state);
    if (s === 'results') el.classList.toggle('rp-results', true);
  });
}

// ── Results renderer ──────────────────────────────────────────────
function renderResults(d) {
  const pg    = d.pricing_gap;
  const depth = d.raw_probability_data?.expected_flood_depth_m;

  // Location
  document.getElementById('res-coords').textContent =
    `${selectedLat?.toFixed(5)}°N  ${selectedLon?.toFixed(5)}°E`;
  if (selectedAddr) document.getElementById('res-addr').textContent = selectedAddr;

  // Gauge
  const prob = d.flood_probability_pct;
  const circumference = 314.16;
  const offset = circumference * (1 - prob / 100);
  const arc = document.getElementById('g-arc');
  arc.style.strokeDashoffset = circumference; // reset first
  setTimeout(() => { arc.style.strokeDashoffset = offset; }, 80);

  const ratingKey = d.risk_rating.toLowerCase().replace(' ', '-');
  arc.style.stroke = { low: '#20a870', medium: '#c89020', high: '#e05a20', 'very-high': '#e02020' }[ratingKey] || '#e8a820';

  document.getElementById('gauge-pct').textContent = `${prob.toFixed(1)}%`;

  const pill = document.getElementById('risk-pill');
  pill.textContent  = d.risk_rating;
  pill.className    = `risk-pill ${ratingKey}`;

  document.getElementById('ga-conf').textContent  = d.confidence || '—';
  document.getElementById('ga-depth').textContent = depth != null ? `${depth.toFixed(2)} m` : '—';

  // Verdict
  renderVerdict(d);

  // Metrics
  document.getElementById('mc-eal').textContent  = `€${fmt(d.expected_annual_loss)}`;
  document.getElementById('mc-rec').textContent  = `€${fmt(d.recommended_premium)}`;
  document.getElementById('mc-curr').textContent = pg?.current_premium != null ? `€${fmt(pg.current_premium)}` : '—';
  document.getElementById('mc-cov').textContent  = pg?.coverage_pct != null ? `${pg.coverage_pct.toFixed(1)}%` : '—';

  // Breakdown bars
  renderBreakdown(d.risk_breakdown, ratingKey);

  // Explanation
  document.getElementById('explanation').textContent = d.explanation || '';

  // Footer
  const ts = d.analysis_timestamp ? new Date(d.analysis_timestamp).toLocaleTimeString('en-GB') : '—';
  document.getElementById('rf-ts').textContent  = ts;
  const src = document.getElementById('rf-src');
  if (d._source === 'mock') {
    src.textContent = 'MOCK DATA';
    src.style.display = '';
  } else {
    src.style.display = 'none';
  }
}

function renderVerdict(d) {
  const pg      = d.pricing_gap;
  const verdict = document.getElementById('verdict');

  if (!pg || pg.verdict == null) {
    verdict.className = 'verdict';
    document.getElementById('v-word').textContent = d.risk_rating;
    document.getElementById('v-sev').textContent  = '';
    document.getElementById('v-num').textContent  = `€${fmt(d.recommended_premium)} / yr`;
    document.getElementById('v-sub').textContent  = 'Recommended annual premium';
    return;
  }

  const v   = pg.verdict.toLowerCase().replace(' ', '-');
  const sev = pg.severity.toLowerCase();
  const cls = v === 'correctly-priced' ? 'correct' : v === 'overpriced' ? 'overpriced' : `underpriced-${sev}`;

  verdict.className = `verdict ${cls}`;

  document.getElementById('v-word').textContent = pg.verdict;
  document.getElementById('v-sev').textContent  = pg.severity;

  const sign = pg.gap_euros > 0 ? '+' : '';
  document.getElementById('v-num').textContent =
    `${sign}€${fmt(pg.gap_euros)}  (${sign}${pg.gap_pct.toFixed(1)}%)`;

  document.getElementById('v-sub').textContent =
    `Recommended: €${fmt(pg.recommended_premium)} / yr · Current: €${fmt(pg.current_premium)} / yr`;
}

function renderBreakdown(breakdown, ratingKey) {
  const barColor = {
    low: '#20a870', medium: '#c89020', high: '#e05a20', 'very-high': '#e02020',
  }[ratingKey] || '#e8a820';

  const container = document.getElementById('breakdown-list');
  container.innerHTML = '';

  Object.entries(breakdown).forEach(([label, pct], i) => {
    const item = document.createElement('div');
    item.className = 'bar-item';
    item.innerHTML = `
      <div class="bar-header">
        <span class="bar-name">${label}</span>
        <span class="bar-pct">${pct.toFixed(1)}%</span>
      </div>
      <div class="bar-track">
        <div class="bar-fill" style="--w:${pct}%; background:${barColor}; animation-delay:${i * 80}ms"></div>
      </div>`;
    container.appendChild(item);
  });
}

// ── Formatting ────────────────────────────────────────────────────
function fmt(n) {
  if (n == null) return '—';
  return Math.round(n).toLocaleString('de-DE');
}

// ── Street view ───────────────────────────────────────────────────
function initStreetView() {
  const btn   = document.getElementById('sv-toggle');
  const panel = document.getElementById('sv-panel');
  const close = document.getElementById('sv-close');
  const frame = document.getElementById('sv-frame');
  const coords = document.getElementById('sv-coords');

  btn.addEventListener('click', () => {
    const isOpen = !panel.classList.contains('hidden');
    if (isOpen) {
      closeStreetView();
    } else {
      openStreetView();
    }
  });

  close.addEventListener('click', closeStreetView);

  function openStreetView() {
    if (!selectedLat) return;
    const url = `https://maps.google.com/maps?q=&layer=c&cbll=${selectedLat},${selectedLon}&cbp=12,0,0,0,0&output=embed`;
    frame.src = url;
    coords.textContent = `${selectedLat.toFixed(5)}°N  ${selectedLon.toFixed(5)}°E`;
    panel.classList.remove('hidden');
    btn.classList.add('sv-active');
    btn.querySelector('span') && (btn.querySelector('span').textContent = 'CLOSE VIEW');
    // shrink map slightly so the panel doesn't fully obscure the marker
    map.invalidateSize();
  }

  function closeStreetView() {
    panel.classList.add('hidden');
    frame.src = '';
    btn.classList.remove('sv-active');
    map.invalidateSize();
  }
}

// ── Bootstrap ─────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initMap();
  initLayerControls();
  initSearch();
  initCoordInputs();
  initStreetView();

  analyzeBtn().addEventListener('click', () => {
    if (!analyzeBtn().disabled) runAnalysis();
  });

  [latInput(), lonInput(), propValInput(), currPremInput()].forEach(el => {
    el.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && selectedLat) runAnalysis();
    });
  });
});
