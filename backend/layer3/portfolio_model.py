"""
Layer 3 — Portfolio Impact Model
=================================
Estimates the financial improvement an insurer gains by adopting HydroRisk
for their full policy portfolio.

Used by:
  - POST /api/portfolio  (optional API endpoint in api.py)
  - frontend portfolio calculator (same math, runs in JS client-side)

All monetary values in euros.
"""

_TARGET_LOSS_RATIO        = 0.65   # fraction of premium that goes to claims
_PLATFORM_COST_PER_POLICY = 0.50   # € per policy per year (HydroRisk API fee)


def calculate_portfolio_impact(
    portfolio_size:           int,
    avg_premium:              float,
    loss_ratio:               float,
    expense_ratio:            float,
    mispriced_pct:            float,
    avg_mispricing:           float,
    platform_cost_per_policy: float = _PLATFORM_COST_PER_POLICY,
) -> dict:
    """
    Calculate the financial impact of adopting HydroRisk on a full portfolio.

    Parameters
    ----------
    portfolio_size          : number of active policies
    avg_premium             : mean annual premium per policy (€)
    loss_ratio              : current claims / premiums (0–1, e.g. 0.85)
    expense_ratio           : operating costs / premiums (0–1, e.g. 0.28)
    mispriced_pct           : share of policies currently mispriced (0–1)
    avg_mispricing          : average annual premium shortfall per mispriced policy (€)
    platform_cost_per_policy: HydroRisk API cost per policy per year (€)

    Returns
    -------
    dict with current state, improved state, and impact metrics.
    All monetary values in euros. Ratios as floats 0–1.

    Key insight
    -----------
    HydroRisk corrects mispriced policies upward. Claims are unchanged
    (the underlying risk hasn't changed), but premium income rises.
    Profit improvement = additional_premium × (1 − expense_ratio)
    because the extra premium income is not subject to claims expense.
    """

    # ── Current state ────────────────────────────────────────────────────────
    total_premiums  = portfolio_size * avg_premium
    total_claims    = total_premiums * loss_ratio
    combined_ratio  = loss_ratio + expense_ratio
    current_profit  = total_premiums * (1 - combined_ratio)

    # ── With HydroRisk ───────────────────────────────────────────────────────
    # Mispriced policies are repriced upward.
    # Claims stay the same (underlying risk unchanged), premium income rises.
    mispriced_policies  = portfolio_size * mispriced_pct
    additional_premium  = mispriced_policies * avg_mispricing
    new_total_premiums  = total_premiums + additional_premium
    new_loss_ratio      = total_claims / new_total_premiums
    new_combined_ratio  = new_loss_ratio + expense_ratio
    new_profit          = new_total_premiums * (1 - new_combined_ratio)

    # ── Impact ───────────────────────────────────────────────────────────────
    # Derivation:
    #   new_profit - current_profit
    #   = [new_total_premiums × (1 - expense_ratio) - total_claims]
    #     - [total_premiums × (1 - expense_ratio) - total_claims]
    #   = additional_premium × (1 - expense_ratio)
    profit_improvement = additional_premium * (1 - expense_ratio)
    platform_cost      = portfolio_size * platform_cost_per_policy
    net_benefit        = profit_improvement - platform_cost
    roi_pct            = (net_benefit / platform_cost * 100) if platform_cost > 0 else 0.0

    return {
        "current": {
            "total_premiums":      round(total_premiums, 2),
            "total_claims":        round(total_claims, 2),
            "loss_ratio":          round(loss_ratio, 4),
            "combined_ratio":      round(combined_ratio, 4),
            "underwriting_result": round(current_profit, 2),
        },
        "improved": {
            "additional_premium":  round(additional_premium, 2),
            "new_total_premiums":  round(new_total_premiums, 2),
            "loss_ratio":          round(new_loss_ratio, 4),
            "combined_ratio":      round(new_combined_ratio, 4),
            "underwriting_result": round(new_profit, 2),
        },
        "impact": {
            "profit_improvement": round(profit_improvement, 2),
            "platform_cost":      round(platform_cost, 2),
            "net_benefit":        round(net_benefit, 2),
            "roi_pct":            round(roi_pct, 1),
            "mispriced_policies": round(mispriced_policies),
        },
    }


# ── Self-test ────────────────────────────────────────────────────────────────
# Run:  python portfolio_model.py
# Expected: profit_improvement ~€5.76M, ROI ~11,420%

if __name__ == "__main__":
    result = calculate_portfolio_impact(
        portfolio_size = 100_000,
        avg_premium    = 1_200,
        loss_ratio     = 0.85,
        expense_ratio  = 0.28,
        mispriced_pct  = 0.20,
        avg_mispricing = 400,
    )

    imp = result["impact"]
    cur = result["current"]
    imp2 = result["improved"]

    print("=" * 50)
    print("  PORTFOLIO IMPACT — validation run")
    print("=" * 50)
    print(f"\n  Current state:")
    print(f"    Total premiums       : €{cur['total_premiums']:>15,.0f}")
    print(f"    Loss ratio           : {cur['loss_ratio']*100:.1f}%")
    print(f"    Combined ratio       : {cur['combined_ratio']*100:.1f}%")
    print(f"    Underwriting result  : €{cur['underwriting_result']:>15,.0f}")

    print(f"\n  With HydroRisk:")
    print(f"    Additional premium   : €{imp2['additional_premium']:>15,.0f}")
    print(f"    New loss ratio       : {imp2['loss_ratio']*100:.1f}%")
    print(f"    Combined ratio       : {imp2['combined_ratio']*100:.1f}%")
    print(f"    Underwriting result  : €{imp2['underwriting_result']:>15,.0f}")

    print(f"\n  Impact:")
    print(f"    Profit improvement   : €{imp['profit_improvement']:>15,.0f}  (expect ~€5,760,000)")
    print(f"    Platform cost        : €{imp['platform_cost']:>15,.0f}  (expect    €50,000)")
    print(f"    Net benefit          : €{imp['net_benefit']:>15,.0f}  (expect ~€5,710,000)")
    print(f"    ROI on platform      :  {imp['roi_pct']:>14,.0f}%  (expect    ~11,420%)")
    print(f"    Mispriced policies   :  {imp['mispriced_policies']:>14,.0f}")

    # Assertions
    assert abs(imp["profit_improvement"] - 5_760_000) < 1_000, "Profit improvement wrong"
    assert imp["platform_cost"]  == 50_000,                    "Platform cost wrong"
    assert abs(imp["roi_pct"] - 11420) < 10,                   "ROI wrong"
    print("\n  OK — all assertions passed.")
