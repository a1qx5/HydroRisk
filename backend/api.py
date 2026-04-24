"""
Person 4 — Flask API
  POST /api/analyze   body: { lat, lon, property_value?, current_premium? }
  GET  /api/health    liveness check
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, request, jsonify
from flask_cors import CORS

from layer1.collector import get_property_data
from layer2.risk_engine import calculate_probability
from layer3.premium_calculator import calculate_premium

app = Flask(__name__)
CORS(app)


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


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

    property_value  = body.get("property_value")
    current_premium = body.get("current_premium")

    if property_value is not None:
        try:
            property_value = float(property_value)
        except (TypeError, ValueError):
            return jsonify({"error": "property_value must be numeric"}), 400

    if current_premium is not None:
        try:
            current_premium = float(current_premium)
        except (TypeError, ValueError):
            return jsonify({"error": "current_premium must be numeric"}), 400

    try:
        property_data    = get_property_data(lat, lon)
        probability_data = calculate_probability(property_data)
        result           = calculate_premium(probability_data, property_value, current_premium)
        result["raw_property_data"] = property_data
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
