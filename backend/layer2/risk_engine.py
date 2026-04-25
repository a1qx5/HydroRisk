"""
Person 3 — Layer 2: Risk Score Engine
Input:  property_data dict (from get_property_data)
Output: {
    annual_flood_probability, flood_probability_pct, risk_rating,
    expected_flood_depth_m, component_scores, weighted_contributions, confidence
}
"""

# Placeholder hero data — replace with get_property_data() at Hour 5
PLACEHOLDER_HERO_DATA = {
    "lat": 46.5670,
    "lon": 26.9146,
    "flood_events_12yr": 6,
    "years_with_flooding": 6,
    "annual_flood_probability_observed": 0.60,
    "flood_direct_hits": 4,
    "flood_history_confidence": "HIGH",
    "elevation_m": 45.0,
    "slope_degrees": 0.5,
    "twi": 11.2,
    "distance_to_river_m": 80.0,
    "is_in_floodplain": True,
    "elevation_percentile": 8.0,
    "terrain_flood_score": 0.85,
    "imperviousness_pct": 0.55,
    "upstream_imperviousness_pct": 0.72,
    "imperviousness_trend": "INCREASING",
    "landuse_flood_score": 0.68,
    "climate_multiplier_2035": 1.25,
    "precipitation_trend": "INCREASING",
    "flood_defense_present": False,
    "defense_protection_level": "NONE",
    "data_freshness_days": 1,
    "analysis_timestamp": "2026-04-24T00:00:00+00:00",
}

_WEIGHTS = {
    "flood_history": 0.35,
    "terrain":       0.25,
    "landuse":       0.20,
    "climate":       0.15,
    "defense":       0.05,
}


def _flood_history_score(d: dict) -> float:
    score = d["annual_flood_probability_observed"]
    if d["flood_history_confidence"] == "LOW":
        score = max(score, 0.05)
    return score


def _terrain_score(d: dict) -> float:
    score = d["terrain_flood_score"]
    dist = d["distance_to_river_m"]
    if dist < 100:
        score += 0.15
    elif dist < 500:
        score += 0.08
    elif dist > 2000:
        score -= 0.05
    if d["is_in_floodplain"]:
        score += 0.10
    return min(1.0, max(0.0, score))


def _landuse_score(d: dict) -> float:
    score = d["landuse_flood_score"]
    trend = d["imperviousness_trend"]
    if trend == "INCREASING":
        score *= 1.20
    elif trend == "DECREASING":
        score *= 0.90
    return min(1.0, max(0.0, score))


def _climate_score(d: dict) -> float:
    return (d["climate_multiplier_2035"] - 1.0) / 0.5


def _defense_score(d: dict) -> float:
    if not d["flood_defense_present"]:
        return 0.50
    return {"HIGH": 0.0, "MEDIUM": 0.2, "LOW": 0.4}.get(d["defense_protection_level"], 0.5)


def _estimate_flood_depth(d: dict) -> float:
    elev = d["elevation_m"]
    imperv = d["upstream_imperviousness_pct"]
    if elev < 50 and imperv > 0.7:
        return 1.5
    if elev < 80 or imperv > 0.5:
        return 0.9
    if elev < 150 or imperv > 0.3:
        return 0.4
    return 0.15


def calculate_probability(property_data: dict) -> dict:
    """Convert raw property data into flood probability with full component breakdown."""
    scores = {
        "flood_history_score": _flood_history_score(property_data),
        "terrain_score":       _terrain_score(property_data),
        "landuse_score":       _landuse_score(property_data),
        "climate_score":       _climate_score(property_data),
        "defense_score":       _defense_score(property_data),
    }

    probability = (
        scores["flood_history_score"] * _WEIGHTS["flood_history"]
        + scores["terrain_score"]     * _WEIGHTS["terrain"]
        + scores["landuse_score"]     * _WEIGHTS["landuse"]
        + scores["climate_score"]     * _WEIGHTS["climate"]
        + scores["defense_score"]     * _WEIGHTS["defense"]
    )
    probability = round(min(1.0, probability), 4)

    if probability < 0.05:
        rating = "LOW"
    elif probability < 0.15:
        rating = "MEDIUM"
    elif probability < 0.35:
        rating = "HIGH"
    else:
        rating = "VERY HIGH"

    if probability > 0:
        contributions = {
            "Flood History": round(scores["flood_history_score"] * _WEIGHTS["flood_history"] / probability * 100, 2),
            "Terrain":       round(scores["terrain_score"]       * _WEIGHTS["terrain"]       / probability * 100, 2),
            "Land Use":      round(scores["landuse_score"]       * _WEIGHTS["landuse"]       / probability * 100, 2),
            "Climate":       round(scores["climate_score"]       * _WEIGHTS["climate"]       / probability * 100, 2),
            "Defenses":      round(scores["defense_score"]       * _WEIGHTS["defense"]       / probability * 100, 2),
        }
    else:
        contributions = {"Flood History": 35.0, "Terrain": 25.0, "Land Use": 20.0, "Climate": 15.0, "Defenses": 5.0}

    has_direct_hits = property_data.get("flood_direct_hits", 0) > 0
    if property_data.get("flood_history_confidence") == "LOW":
        confidence = "LOW"
    elif has_direct_hits:
        confidence = "HIGH"
    else:
        confidence = "MEDIUM"

    return {
        "annual_flood_probability": probability,
        "flood_probability_pct":    round(probability * 100, 2),
        "risk_rating":              rating,
        "expected_flood_depth_m":   _estimate_flood_depth(property_data),
        "component_scores":         scores,
        "weighted_contributions":   contributions,
        "confidence":               confidence,
    }
