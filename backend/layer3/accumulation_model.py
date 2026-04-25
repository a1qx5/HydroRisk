"""
Layer 3 — Accumulation Risk Model
===================================
Identifies geographic concentrations of high-risk policies.
A portfolio of 500 HIGH-risk policies spread across Romania is manageable.
A portfolio of 500 HIGH-risk policies all in the same Siret River catchment
is a catastrophe accumulation: one flood event wipes them all simultaneously.

Input:  list of policy dicts, each containing:
        { lat, lon, property_value, annual_flood_probability, risk_rating }

Output: {
    clusters:           list of grid cell summaries,
    portfolio_summary:  aggregate accumulation metrics,
    critical_zones:     cells exceeding accumulation thresholds,
    reinsurance_advice: human-readable flags
}
"""

from collections import defaultdict
from math import floor

GRID_SIZE            = 0.01        # ~1 km grid cells at 45°N latitude
CRITICAL_EXPOSURE    = 5_000_000   # €5M aggregate exposure in one cell = critical
CRITICAL_POLICY_COUNT = 10         # 10+ policies in one cell = concentration flag
HIGH_RISK_THRESHOLD  = 0.35        # annual_flood_probability above this = high risk


def _cell_key(lat: float, lon: float) -> tuple:
    """Snap coordinates to the nearest grid cell centre."""
    return (
        round(floor(lat / GRID_SIZE) * GRID_SIZE + GRID_SIZE / 2, 6),
        round(floor(lon / GRID_SIZE) * GRID_SIZE + GRID_SIZE / 2, 6),
    )


def calculate_accumulation_risk(policies: list) -> dict:
    """
    Cluster policies into grid cells and calculate accumulation exposure.

    Each policy dict must contain: lat, lon, property_value,
    annual_flood_probability, risk_rating.

    Max Probable Loss (MPL) is the industry-standard term for the largest
    single-event loss a portfolio can sustain. Each cell's MPL assumes full
    correlation (all policies in the cell flood simultaneously — realistic
    for a 1 km² area hit by the same flood event).
    """
    if not policies:
        return {"error": "No policies provided", "clusters": [], "portfolio_summary": {}}

    # ── Step 1: Snap each policy to its grid cell ─────────────────────────────
    cells = defaultdict(list)
    for policy in policies:
        key = _cell_key(float(policy["lat"]), float(policy["lon"]))
        cells[key].append(policy)

    # ── Step 2: Compute metrics per cell ──────────────────────────────────────
    clusters = []
    for (cell_lat, cell_lon), cell_policies in cells.items():
        n           = len(cell_policies)
        total_value = sum(float(p["property_value"]) for p in cell_policies)
        avg_prob    = sum(float(p["annual_flood_probability"]) for p in cell_policies) / n
        high_risk_count = sum(
            1 for p in cell_policies
            if float(p["annual_flood_probability"]) >= HIGH_RISK_THRESHOLD
        )
        high_risk_pct = high_risk_count / n

        # MPL: assume flood hits entire cell simultaneously (correlation = 1).
        # avg_damage_fraction defaults to 0.44 (JRC 1 m depth curve midpoint).
        avg_damage_fraction = sum(
            float(p.get("damage_fraction", 0.44)) for p in cell_policies
        ) / n
        max_probable_loss = total_value * avg_damage_fraction * avg_prob

        # ── Severity classification ────────────────────────────────────────────
        if total_value >= CRITICAL_EXPOSURE or n >= CRITICAL_POLICY_COUNT:
            severity = "CRITICAL" if avg_prob >= HIGH_RISK_THRESHOLD else "HIGH"
        elif total_value >= CRITICAL_EXPOSURE * 0.4 or n >= 5:
            severity = "MEDIUM"
        else:
            severity = "LOW"

        clusters.append({
            "cell_lat":              cell_lat,
            "cell_lon":              cell_lon,
            "policy_count":          n,
            "total_insured_value":   round(total_value, 2),
            "avg_flood_probability": round(avg_prob, 4),
            "high_risk_policy_pct":  round(high_risk_pct * 100, 1),
            "max_probable_loss":     round(max_probable_loss, 2),
            "accumulation_severity": severity,
        })

    # ── Step 3: Sort by MPL descending (worst first) ──────────────────────────
    clusters.sort(key=lambda c: c["max_probable_loss"], reverse=True)

    critical_zones = [c for c in clusters if c["accumulation_severity"] == "CRITICAL"]
    high_zones     = [c for c in clusters if c["accumulation_severity"] == "HIGH"]

    total_policies       = len(policies)
    total_value          = sum(float(p["property_value"]) for p in policies)
    policies_in_critical = sum(c["policy_count"] for c in critical_zones)
    value_in_critical    = sum(c["total_insured_value"] for c in critical_zones)
    worst_mpl            = clusters[0]["max_probable_loss"] if clusters else 0

    # ── Step 4: Reinsurance advice ────────────────────────────────────────────
    reinsurance_advice = []
    if critical_zones:
        reinsurance_advice.append(
            f"{len(critical_zones)} critical accumulation zone(s) identified. "
            f"Single-event MPL of EUR{worst_mpl:,.0f} likely exceeds individual risk retention."
        )
    if total_policies > 0 and policies_in_critical / total_policies > 0.3:
        reinsurance_advice.append(
            f"{policies_in_critical / total_policies:.0%} of portfolio sits in critical zones. "
            "Geographic diversification needed before next reinsurance renewal."
        )
    if not reinsurance_advice:
        reinsurance_advice.append(
            "Portfolio accumulation is within normal bounds. No urgent geographic flags."
        )

    return {
        "clusters":      clusters,
        "critical_zones": critical_zones,
        "high_zones":    high_zones,
        "portfolio_summary": {
            "total_policies":             total_policies,
            "total_cells":                len(clusters),
            "total_insured_value":        round(total_value, 2),
            "policies_in_critical_zones": policies_in_critical,
            "value_in_critical_zones":    round(value_in_critical, 2),
            "worst_cell_mpl":             round(worst_mpl, 2),
            "critical_zone_count":        len(critical_zones),
            "high_zone_count":            len(high_zones),
        },
        "reinsurance_advice": reinsurance_advice,
    }


# ── Self-test ─────────────────────────────────────────────────────────────────
# Run:  python accumulation_model.py
# Expected: Bacau cluster = CRITICAL, Bucharest = HIGH or MEDIUM

if __name__ == "__main__":
    import json
    import random

    random.seed(42)
    mock_policies = []

    # Cluster A — Bacau riverside: 15 high-risk policies
    for _ in range(15):
        mock_policies.append({
            "lat":                    46.567 + random.uniform(-0.003, 0.003),
            "lon":                    26.914 + random.uniform(-0.003, 0.003),
            "property_value":         random.uniform(150_000, 300_000),
            "annual_flood_probability": random.uniform(0.50, 0.80),
            "risk_rating":            "VERY HIGH",
            "damage_fraction":        0.59,
        })

    # Cluster B — Bucharest suburb: 8 medium-risk policies
    for _ in range(8):
        mock_policies.append({
            "lat":                    44.450 + random.uniform(-0.003, 0.003),
            "lon":                    26.100 + random.uniform(-0.003, 0.003),
            "property_value":         random.uniform(200_000, 400_000),
            "annual_flood_probability": random.uniform(0.30, 0.55),
            "risk_rating":            "HIGH",
            "damage_fraction":        0.44,
        })

    # Scattered low-risk — spread across Romania
    for _ in range(20):
        mock_policies.append({
            "lat":                    45.5 + random.uniform(-2, 2),
            "lon":                    25.0 + random.uniform(-3, 3),
            "property_value":         random.uniform(80_000, 150_000),
            "annual_flood_probability": random.uniform(0.02, 0.12),
            "risk_rating":            "LOW",
            "damage_fraction":        0.13,
        })

    result = calculate_accumulation_risk(mock_policies)

    print("=" * 55)
    print("  ACCUMULATION MODEL SELF-TEST")
    print("=" * 55)
    print("\nPortfolio summary:")
    print(json.dumps(result["portfolio_summary"], indent=2))
    print(f"\nTop cluster (expect Bacau, CRITICAL):")
    top = result["clusters"][0]
    print(f"  severity  : {top['accumulation_severity']}")
    print(f"  policies  : {top['policy_count']}")
    print(f"  total val : EUR{top['total_insured_value']:,.0f}")
    print(f"  avg prob  : {top['avg_flood_probability']*100:.1f}%")
    print(f"  MPL       : EUR{top['max_probable_loss']:,.0f}")
    print(f"\nReinsurance advice:")
    for line in result["reinsurance_advice"]:
        print(f"  - {line}")

    # Assertions
    assert top["accumulation_severity"] == "CRITICAL", \
        f"Expected CRITICAL, got {top['accumulation_severity']}"
    assert result["portfolio_summary"]["critical_zone_count"] >= 1, \
        "Expected at least 1 critical zone"
    assert result["portfolio_summary"]["total_policies"] == 43, \
        "Expected 43 total policies"

    print("\nOK - All assertions passed.")
