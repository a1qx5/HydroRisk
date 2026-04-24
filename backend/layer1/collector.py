"""
Person 2 — Master Function: get_property_data(lat, lon)
Calls all 5 lenses in parallel, merges results, validates ranges.
Never crashes — falls back to defaults on any lens failure.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from .flood_history import get_flood_history
from .terrain import get_terrain_data
from .landuse import get_landuse_data
from .climate import get_climate_data
from .defenses import get_defense_data

_DEFAULTS = {
    "flood_events_10yr": 0,
    "years_with_flooding": 0,
    "annual_flood_probability_observed": 0.05,
    "flood_direct_hits": 0,
    "flood_history_confidence": "LOW",
    "elevation_m": 100.0,
    "slope_degrees": 2.0,
    "twi": 6.0,
    "distance_to_river_m": 1000.0,
    "is_in_floodplain": False,
    "elevation_percentile": 50.0,
    "terrain_flood_score": 0.3,
    "imperviousness_pct": 0.3,
    "upstream_imperviousness_pct": 0.3,
    "imperviousness_trend": "STABLE",
    "landuse_flood_score": 0.3,
    "climate_multiplier_2035": 1.18,
    "precipitation_trend": "INCREASING",
    "flood_defense_present": False,
    "defense_protection_level": "NONE",
}

_VALIDATORS = {
    "annual_flood_probability_observed": (0.0, 1.0),
    "twi":                               (0.0, 15.0),
    "terrain_flood_score":               (0.0, 1.0),
    "imperviousness_pct":                (0.0, 1.0),
    "upstream_imperviousness_pct":       (0.0, 1.0),
    "landuse_flood_score":               (0.0, 1.0),
    "climate_multiplier_2035":           (1.0, 1.5),
    "elevation_m":                       (-50.0, 2600.0),  # Romania: Black Sea to Moldoveanu
}


def get_property_data(lat: float, lon: float) -> dict:
    """Collect all 5 data lenses in parallel and return merged property dict."""
    lenses = {
        "flood_history": lambda: get_flood_history(lat, lon),
        "terrain":       lambda: get_terrain_data(lat, lon),
        "landuse":       lambda: get_landuse_data(lat, lon),
        "climate":       lambda: get_climate_data(lat, lon),
        "defenses":      lambda: get_defense_data(lat, lon),
    }

    lens_results = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fn): name for name, fn in lenses.items()}
        for future in as_completed(futures):
            name = futures[future]
            try:
                lens_results[name] = future.result()
            except Exception as exc:
                print(f"[WARN] Lens '{name}' failed: {exc} — using defaults")
                lens_results[name] = {}

    merged = {"lat": lat, "lon": lon}
    for data in lens_results.values():
        merged.update(data)

    for key, default in _DEFAULTS.items():
        merged.setdefault(key, default)

    for key, (lo, hi) in _VALIDATORS.items():
        if key in merged and isinstance(merged[key], (int, float)):
            merged[key] = max(lo, min(hi, merged[key]))

    merged["data_freshness_days"] = 1
    merged["analysis_timestamp"] = datetime.now(timezone.utc).isoformat()

    return merged
