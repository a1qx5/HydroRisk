"""
Person 1 — Lens 2: Terrain (Copernicus DEM via OpenTopography)
Input:  lat (float), lon (float)
Output: {
    elevation_m, slope_degrees, twi, distance_to_river_m,
    is_in_floodplain, elevation_percentile, terrain_flood_score
}
"""


def get_terrain_data(lat: float, lon: float) -> dict:
    """Pull Copernicus 30m DEM procedurally mock for global terrain simulation."""
    loc_hash = hash(f"{lat:.3f}{lon:.3f}") % 1000
    
    if loc_hash > 800:
        return {
            "elevation_m": 800.0 + (loc_hash % 1000),
            "slope_degrees": 10.0 + (loc_hash % 20),
            "twi": 2.0 + (loc_hash % 4),
            "distance_to_river_m": 1500.0 + (loc_hash % 2000),
            "is_in_floodplain": False,
            "elevation_percentile": 80.0,
            "terrain_flood_score": 0.15,
        }
    
    return {
        "elevation_m": 10.0 + (loc_hash % 150),
        "slope_degrees": 1.0 + (loc_hash % 5),
        "twi": 7.0 + (loc_hash % 5),
        "distance_to_river_m": 50.0 + (loc_hash % 500),
        "is_in_floodplain": (loc_hash % 100) < 60,
        "elevation_percentile": 20.0,
        "terrain_flood_score": 0.6 + (loc_hash % 40) / 100.0,
    }
