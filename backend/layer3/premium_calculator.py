"""
Layer 3: Premium Calculator
Input:  probability_data dict (from calculate_probability),
        property_value (float, €) — must be provided; falls back to Romanian average if missing,
        current_premium (float, €, optional),
        loss_ratio (float, optional) — insurer-specific target; defaults to 0.65
Output: full premium recommendation dict (see CLAUDE.md Layer 3 → Frontend contract)

Depth-damage curve: JRC European Flood Damage Functions for residential buildings.
  Source: Huizinga et al. (2017), Joint Research Centre, EU.
Loss ratio: fraction of premium that goes to paying claims (rest = admin + profit).
  0.65 is the EU non-life flood insurance benchmark; individual insurers vary 0.60–0.75.
"""
from datetime import datetime, timezone

# JRC European Flood Damage Functions — residential buildings
# (depth_metres, damage_fraction_of_property_value)
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

_DEFAULT_LOSS_RATIO     = 0.65       # EU flood insurance benchmark
_DEFAULT_PROPERTY_VALUE = 150_000    # € — Romanian residential average (fallback only)


def _depth_damage_fraction(depth_m: float) -> float:
    """Linear interpolation of JRC damage fraction for a given flood depth."""
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


def _top_driver(weighted_contributions: dict) -> tuple[str, float]:
    """Return the name and percentage of the largest risk contributor."""
    driver = max(weighted_contributions, key=weighted_contributions.get)
    return driver, weighted_contributions[driver]


def _generate_explanation(
    probability_data: dict,
    eal: float,
    recommended_premium: float,
    current_premium: float | None,
) -> str:
    prob_pct = probability_data["flood_probability_pct"]
    rating   = probability_data["risk_rating"]
    driver, driver_pct = _top_driver(probability_data["weighted_contributions"])

    lines = [
        f"This property carries a {prob_pct:.1f}% annual flood probability ({rating} risk).",
        f"The primary risk driver is {driver}, accounting for {driver_pct:.1f}% of the total risk score.",
        f"Expected annual loss: €{eal:,.0f}.",
    ]

    if current_premium and current_premium > 0 and eal > 0:
        coverage_pct = current_premium / eal * 100
        gap          = recommended_premium - current_premium
        if gap > 0:
            lines.append(
                f"The current premium of €{current_premium:,.0f} covers only "
                f"{coverage_pct:.1f}% of expected annual losses — "
                f"the policy is underpriced by €{gap:,.0f}."
            )
        else:
            lines.append(
                f"The recommended premium of €{recommended_premium:,.0f} is below "
                f"the current premium of €{current_premium:,.0f}."
            )

    return " ".join(lines)


def calculate_premium(
    probability_data: dict,
    property_value: float = None,
    current_premium: float = None,
    loss_ratio: float = None,
) -> dict:
    """Calculate recommended flood insurance premium and pricing gap vs current premium."""
    prop_value        = property_value if property_value is not None else _DEFAULT_PROPERTY_VALUE
    prop_value_source = "PROVIDED" if property_value is not None else "DEFAULT_ESTIMATE"
    target_loss_ratio = loss_ratio if loss_ratio is not None else _DEFAULT_LOSS_RATIO

    prob  = probability_data["annual_flood_probability"]
    depth = probability_data["expected_flood_depth_m"]

    damage_fraction           = _depth_damage_fraction(depth)
    expected_damage_per_event = prop_value * damage_fraction
    expected_annual_loss      = prob * expected_damage_per_event
    recommended_premium       = expected_annual_loss / target_loss_ratio

    # ── Pricing gap ────────────────────────────────────────────────────────────
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

        severity = (
            "MINOR"       if abs_gap_pct < 20  else
            "SIGNIFICANT" if abs_gap_pct < 50  else
            "MAJOR"       if abs_gap_pct < 100 else
            "CRITICAL"
        )

        coverage_pct = (current_premium / expected_annual_loss * 100) if expected_annual_loss > 0 else 0.0

        pricing_gap = {
            "current_premium":     round(current_premium, 2),
            "recommended_premium": round(recommended_premium, 2),
            "gap_euros":           round(gap_euros, 2),
            "gap_pct":             round(gap_pct, 2),
            "verdict":             verdict,
            "severity":            severity,
            "coverage_pct":        round(coverage_pct, 2),
        }
    else:
        pricing_gap = {
            "current_premium":     None,
            "recommended_premium": round(recommended_premium, 2),
            "gap_euros":           None,
            "gap_pct":             None,
            "verdict":             None,
            "severity":            None,
            "coverage_pct":        None,
        }

    # ── Top driver (for prominent frontend display) ────────────────────────────
    driver_name, driver_pct = _top_driver(probability_data["weighted_contributions"])

    result = {
        "flood_probability_pct":      probability_data["flood_probability_pct"],
        "risk_rating":                probability_data["risk_rating"],
        "recommended_premium":        round(recommended_premium, 2),
        "expected_annual_loss":       round(expected_annual_loss, 2),
        "expected_damage_per_event":  round(expected_damage_per_event, 2),
        "damage_fraction_pct":        round(damage_fraction * 100, 2),
        "property_value_used":        round(prop_value, 2),
        "property_value_source":      prop_value_source,
        "loss_ratio_used":            target_loss_ratio,
        "pricing_gap":                pricing_gap,
        "risk_breakdown":             probability_data["weighted_contributions"],
        "top_risk_driver":            {"name": driver_name, "pct": round(driver_pct, 1)},
        "explanation":                _generate_explanation(
                                          probability_data,
                                          expected_annual_loss,
                                          recommended_premium,
                                          current_premium,
                                      ),
        "raw_probability_data":       probability_data,
        "confidence":                 probability_data["confidence"],
        "analysis_timestamp":         datetime.now(timezone.utc).isoformat(),
    }

    if prob < 0.02:
        result["low_risk_note"] = (
            "Standalone flood coverage may not be economically viable at this risk level."
        )

    return result
