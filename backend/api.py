"""
Flask API
  POST /api/analyze   body: { lat, lon, property_value?, current_premium?, loss_ratio? }
  POST /api/demo      body: { property_value?, current_premium?, loss_ratio? }
                      Uses hardcoded hero data — works without Layer 1 or 2 being ready.
  GET  /api/health    liveness check
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, request, jsonify
from flask_cors import CORS

from layer2.risk_engine import calculate_probability
from layer3.premium_calculator import calculate_premium

app = Flask(__name__)
CORS(app)

# ── Hero placeholder (Bacău riverside — worst-case flood zone) ─────────────────
# Simulates realistic Layer 1 output for the demo location.
# Swap out once Layer 1 is integrated.
_HERO_PROPERTY_DATA = {
    "lat": 46.5670,
    "lon": 26.9146,
    # Lens 1 — Flood History (Sentinel-1)
    "flood_events_10yr":                  6,
    "years_with_flooding":                6,
    "annual_flood_probability_observed":  0.60,
    "flood_direct_hits":                  4,
    "flood_history_confidence":           "HIGH",
    # Lens 2 — Terrain (Copernicus DEM)
    "elevation_m":                        45.0,
    "slope_degrees":                      0.5,
    "twi":                                11.2,
    "distance_to_river_m":               80.0,
    "is_in_floodplain":                  True,
    "elevation_percentile":               8.0,
    "terrain_flood_score":               0.85,
    # Lens 3 — Land Use
    "imperviousness_pct":                0.55,
    "upstream_imperviousness_pct":       0.72,
    "imperviousness_trend":              "INCREASING",
    "landuse_flood_score":               0.68,
    # Lens 4 — Climate
    "climate_multiplier_2035":           1.25,
    "precipitation_trend":               "INCREASING",
    # Lens 5 — Defenses
    "flood_defense_present":             False,
    "defense_protection_level":          "NONE",
    # Metadata
    "data_freshness_days":               1,
    "analysis_timestamp":                "2026-04-24T00:00:00+00:00",
}


def _parse_floats(body: dict, *keys) -> tuple:
    """Parse optional float fields from request body. Returns (values..., error_response | None)."""
    results = []
    for key in keys:
        val = body.get(key)
        if val is not None:
            try:
                val = float(val)
            except (TypeError, ValueError):
                return (*[None] * len(keys), (jsonify({"error": f"{key} must be numeric"}), 400))
        results.append(val)
    return (*results, None)


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/api/demo", methods=["POST"])
def demo():
    """Full pipeline using hardcoded hero property data. Works without Layer 1 or 2 ready."""
    body = request.get_json(force=True, silent=True) or {}
    property_value, current_premium, loss_ratio, err = _parse_floats(body, "property_value", "current_premium", "loss_ratio")
    if err:
        return err

    try:
        probability_data = calculate_probability(_HERO_PROPERTY_DATA)
        result           = calculate_premium(probability_data, property_value, current_premium, loss_ratio)
        result["raw_property_data"] = _HERO_PROPERTY_DATA
        result["demo_mode"]         = True
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/analyze", methods=["POST"])
def analyze():
    body = request.get_json(force=True, silent=True) or {}

    lat = body.get("lat")
    lon = body.get("lon")
    if lat is None or lon is None:
        return jsonify({"error": "lat and lon are required"}), 400

    try:
        lat = float(lat)
        lon = float(lon)
    except (TypeError, ValueError):
        return jsonify({"error": "lat and lon must be numeric"}), 400

    property_value, current_premium, loss_ratio, err = _parse_floats(body, "property_value", "current_premium", "loss_ratio")
    if err:
        return err

    try:
        from layer1.collector import get_property_data
        property_data    = get_property_data(lat, lon)
        probability_data = calculate_probability(property_data)
        result           = calculate_premium(probability_data, property_value, current_premium, loss_ratio)
        result["raw_property_data"] = property_data
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
