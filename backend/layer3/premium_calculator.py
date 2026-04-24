"""
Person 4 — Layer 3: Premium Calculator
Input:  probability_data dict (from calculate_probability),
        property_value (float, €, optional),
        current_premium (float, €, optional)
Output: full premium recommendation dict (see CLAUDE.md Layer 3 → Frontend contract)

Depth-damage curve: JRC European Flood Damage Functions for residential buildings.
Loss ratio target: 0.65 (standard flood insurance economics).
"""
from datetime import datetime, timezone

# JRC European Flood Damage Functions — residential buildings
# Source: Joint Research Centre, EU (Huizinga et al. 2017)
_JRC_CURVE = [
    (0.10, 0.04),
    (0.30, 0.13),
    (0.50, 0.22),
    (0.75, 0.33),
    (1.00, 0.44),
    (1.50, 0.59),
    (2.00, 0.70),
    (3.00, 0.83),
]

_LOSS_RATIO = 0.65           # 65% of premium goes to claims; 35% = admin + profit
_DEFAULT_PROPERTY_VALUE = 150_000  # € — Romanian residential average

# Placeholder hero probability — replace with calculate_probability() at Hour 5
PLACEHOLDER_HERO_PROB = {
    "annual_flood_probability": 0.608,
    "flood_probability_pct":    60.8,
    "risk_rating":              "VERY HIGH",
    "expected_flood_depth_m":   1.1,
    "component_scores": {
        "flood_history_score": 0.60,
        "terrain_score":       0.95,
        "landuse_score":       0.82,
        "climate_score":       0.50,
        "defense_score":       0.50,
    },
    "weighted_contributions": {
        "Flood History": 34.4,
        "Terrain":       38.7,
        "Land Use":      16.7,
        "Climate":        8.1,
        "Defenses":       2.0,
    },
    "confidence": "HIGH",
}


def _depth_damage_fraction(depth_m: float) -> float:
    """Interpolate JRC damage fraction for a given flood depth (metres)."""
    if depth_m <= 0 or depth_m < _JRC_CURVE[0][0]:
        return 0.0
    if depth_m >= _JRC_CURVE[-1][0]:
        return 0.97
    for i in range(len(_JRC_CURVE) - 1):
        d0, f0 = _JRC_CURVE[i]
        d1, f1 = _JRC_CURVE[i + 1]
        if d0 <= depth_m <= d1:
            t = (depth_m - d0) / (d1 - d0)
            return f0 + t * (f1 - f0)
    return 0.97


def calculate_premium(
    probability_data: dict,
    property_value: float = None,
    current_premium: float = None,
) -> dict:
    """Calculate recommended flood insurance premium and pricing gap vs current premium."""
    prop_value = property_value if property_value is not None else _DEFAULT_PROPERTY_VALUE
    prop_value_source = "PROVIDED" if property_value is not None else "DEFAULT_ESTIMATE"

    prob  = probability_data["annual_flood_probability"]
    depth = probability_data["expected_flood_depth_m"]

    damage_fraction          = _depth_damage_fraction(depth)
    expected_damage_per_event = prop_value * damage_fraction
    expected_annual_loss     = prob * expected_damage_per_event
    recommended_premium      = expected_annual_loss / _LOSS_RATIO

    if current_premium is not None:
        gap_euros   = recommended_premium - current_premium
        gap_pct     = (gap_euros / current_premium * 100) if current_premium > 0 else 0.0
        abs_gap_pct = abs(gap_pct)

        if abs_gap_pct <= 10:
            verdict = "CORRECTLY PRICED"
        elif gap_euros > 0:
            verdict = "UNDERPRICED"
        else:
            verdict = "OVERPRICED"

        if abs_gap_pct < 20:
            severity = "MINOR"
        elif abs_gap_pct < 50:
            severity = "SIGNIFICANT"
        elif abs_gap_pct < 100:
            severity = "MAJOR"
        else:
            severity = "CRITICAL"

        pricing_gap = {
            "current_premium":     round(current_premium, 2),
            "recommended_premium": round(recommended_premium, 2),
            "gap_euros":           round(gap_euros, 2),
            "gap_pct":             round(gap_pct, 2),
            "verdict":             verdict,
            "severity":            severity,
        }
    else:
        pricing_gap = {
            "current_premium":     None,
            "recommended_premium": round(recommended_premium, 2),
            "gap_euros":           None,
            "gap_pct":             None,
            "verdict":             None,
            "severity":            None,
        }

    result = {
        "flood_probability_pct":      probability_data["flood_probability_pct"],
        "risk_rating":                probability_data["risk_rating"],
        "recommended_premium":        round(recommended_premium, 2),
        "expected_annual_loss":       round(expected_annual_loss, 2),
        "expected_damage_per_event":  round(expected_damage_per_event, 2),
        "damage_fraction_pct":        round(damage_fraction * 100, 2),
        "pricing_gap":                pricing_gap,
        "risk_breakdown":             probability_data["weighted_contributions"],
        "raw_property_data":          {},   # filled in by api.py
        "raw_probability_data":       probability_data,
        "confidence":                 probability_data["confidence"],
        "data_freshness_days":        1,
        "analysis_timestamp":         datetime.now(timezone.utc).isoformat(),
        "property_value_source":      prop_value_source,
    }

    if prob < 0.02:
        result["low_risk_note"] = (
            "Standalone flood coverage may not be economically viable at this risk level."
        )

    return result
