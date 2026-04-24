"""
Person 2 — Lens 3: Land Use / Imperviousness (EEA WMS)
Input:  lat (float), lon (float)
Output: {
    imperviousness_pct, upstream_imperviousness_pct,
    imperviousness_trend, landuse_flood_score
}
"""


def get_landuse_data(lat: float, lon: float) -> dict:
    """Query EEA High Resolution Imperviousness Density WMS for local and upstream zones."""
    # TODO: implement EEA WMS HTTP requests
    # - Local:    500m radius box → average pixel values / 100
    # - Upstream: 1–2km upstream (higher-elevation direction) → average pixel values / 100
    # - Trend:    compare 2006 vs 2018 datasets if accessible
    #             >10pp increase in 5yr upstream → INCREASING
    # - Score:    upstream_imperviousness * 0.6 + local_imperviousness * 0.4
    #             multiply by 1.2 if INCREASING trend, normalize 0–1
    return {
        "imperviousness_pct": 0.3,
        "upstream_imperviousness_pct": 0.3,
        "imperviousness_trend": "STABLE",
        "landuse_flood_score": 0.3,
    }
