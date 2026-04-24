"""
Person 1 — Lens 1: Flood History (Sentinel-1 SAR)
Input:  lat (float), lon (float)
Output: {
    flood_events_10yr, years_with_flooding,
    annual_flood_probability_observed, flood_direct_hits,
    flood_history_confidence
}
"""


def get_flood_history(lat: float, lon: float) -> dict:
    """Search Sentinel-1 SAR archive (2014–today) for flood events near this property."""
    # TODO: implement Sentinel Hub API calls
    # - Define 2km bounding box around (lat, lon)
    # - Query VV band year by year, spring (Mar–May) + autumn (Sep–Nov) windows
    # - Threshold: VV < 0.03 linear = water pixel
    # - Direct hit: centre pixels show water
    # - Near miss: >30% of box shows water
    # - Count distinct years with at least one detection
    return {
        "flood_events_10yr": 0,
        "years_with_flooding": 0,
        "annual_flood_probability_observed": 0.0,
        "flood_direct_hits": 0,
        "flood_history_confidence": "LOW",
    }
