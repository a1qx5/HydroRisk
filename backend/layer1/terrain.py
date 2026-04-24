"""
Person 1 — Lens 2: Terrain (Copernicus DEM via OpenTopography)
Input:  lat (float), lon (float)
Output: {
    elevation_m, slope_degrees, twi, distance_to_river_m,
    is_in_floodplain, elevation_percentile, terrain_flood_score
}
"""


def get_terrain_data(lat: float, lon: float) -> dict:
    """Pull Copernicus 30m DEM for 5km box and compute TWI + terrain flood score."""
    # TODO: implement OpenTopography API call
    # - Request COP30 DEM for 5km bounding box
    # - Extract elevation at (lat, lon), compute local percentile
    # - Calculate slope from surrounding gradient
    # - Calculate TWI: ln(flow_accumulation / tan(slope))
    # - Identify nearest channel (lowest continuous valley path)
    # - Floodplain: elevation within 3m of channel AND within 1km horizontally
    # - Combine into terrain_flood_score (0–1)
    return {
        "elevation_m": 100.0,
        "slope_degrees": 2.0,
        "twi": 6.0,
        "distance_to_river_m": 1000.0,
        "is_in_floodplain": False,
        "elevation_percentile": 50.0,
        "terrain_flood_score": 0.3,
    }
