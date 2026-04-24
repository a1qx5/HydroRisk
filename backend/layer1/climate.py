"""
Person 2 — Lens 4: Climate (RCP 4.5 regional lookup table, projected to 2035)
Input:  lat (float), lon (float)
Output: {
    climate_multiplier_2035,
    precipitation_trend
}
"""


def get_climate_data(lat: float, lon: float) -> dict:
    """Return climate multiplier from published RCP 4.5 regional averages for Romania."""
    # Eastern Romania  (lon > 27)   — largest projected increase in extreme rainfall
    if lon > 27:
        multiplier = 1.25
    # Southern Romania (lat < 45)   — Danube plain, significant summer flooding increase
    elif lat < 45:
        multiplier = 1.20
    # Central Romania  (lat ≥ 45, 23 ≤ lon ≤ 27) — Transylvania, moderate increase
    elif 23 <= lon <= 27:
        multiplier = 1.18
    # Western Romania  (lon < 23)   — Atlantic patterns moderate the impact
    else:
        multiplier = 1.15

    return {
        "climate_multiplier_2035": multiplier,
        "precipitation_trend": "INCREASING",
    }
