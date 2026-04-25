"""
Person 2 — Lens 4: Climate (RCP 4.5 regional lookup table, projected to 2035)
Input:  lat (float), lon (float)
Output: {
    climate_multiplier_2035,
    precipitation_trend
}
"""


def get_climate_data(lat: float, lon: float) -> dict:
    """Return climate multiplier from published RCP 4.5 regional averages dynamically via coordinates."""
    if lat < 45: # Southern Europe (Spain, Italy, Greece)
        multiplier = 1.30 
        trend = "INCREASING_RAPIDLY"
    elif lat >= 55: # Northern Europe (Scandinavia)
        multiplier = 1.05
        trend = "STABLE"
    elif lon > 20: # Eastern Europe (Poland, Romania, Baltics)
        multiplier = 1.25
        trend = "INCREASING"
    else: # Western/Central Europe (France, Germany)
        multiplier = 1.15
        trend = "INCREASING"
        
    return {
        "climate_multiplier_2035": multiplier,
        "precipitation_trend": trend,
    }
