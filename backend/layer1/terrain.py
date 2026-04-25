"""
Person 1 — Lens 2: Terrain (Copernicus DEM via OpenTopography)
Input:  lat (float), lon (float)
Output: {
    elevation_m, slope_degrees, twi, distance_to_river_m,
    is_in_floodplain, elevation_percentile, terrain_flood_score
}
"""

import io
import math

import numpy as np
import requests
import rasterio
import rasterio.transform
from backend.config import OPENTOPOGRAPHY_API_KEY


def _fetch_dem(lat: float, lon: float, margin_km: float = 5.0):
    """Returns (2D numpy array of elevation metres, affine transform)."""
    lat_margin = margin_km / 111.0
    lon_margin = margin_km / (111.0 * math.cos(math.radians(lat)))

    params = {
        "demtype": "COP30",
        "south": lat - lat_margin,
        "north": lat + lat_margin,
        "west": lon - lon_margin,
        "east": lon + lon_margin,
        "outputFormat": "GTiff",
        "API_Key": OPENTOPOGRAPHY_API_KEY,
    }
    response = requests.get(
        "https://portal.opentopography.org/API/globaldem",
        params=params,
        timeout=30,
    )
    response.raise_for_status()

    with rasterio.open(io.BytesIO(response.content)) as src:
        dem = src.read(1).astype(float)
        transform = src.transform
    return dem, transform


def _property_cell(dem, transform, lat: float, lon: float):
    """Convert lat/lon to (row, col) index in the DEM grid, clamped to bounds."""
    row, col = rasterio.transform.rowcol(transform, lon, lat)
    row = max(0, min(dem.shape[0] - 1, row))
    col = max(0, min(dem.shape[1] - 1, col))
    return int(row), int(col)


def _elevation_percentile(dem, row: int, col: int):
    """Returns (elevation_m, percentile 0–100). Filters NoData (< -9000)."""
    elev = dem[row, col]
    valid = dem[dem > -9000]
    percentile = float(np.sum(valid < elev) / len(valid) * 100)
    return float(elev), round(percentile, 1)


def _slope_degrees(dem, row: int, col: int, cell_size_m: float = 30.0) -> float:
    """Central-difference slope at (row, col) in degrees."""
    r = max(1, min(dem.shape[0] - 2, row))
    c = max(1, min(dem.shape[1] - 2, col))

    dz_dx = (dem[r, c + 1] - dem[r, c - 1]) / (2 * cell_size_m)
    dz_dy = (dem[r + 1, c] - dem[r - 1, c]) / (2 * cell_size_m)
    slope_rad = np.arctan(np.sqrt(dz_dx ** 2 + dz_dy ** 2))
    return float(np.degrees(slope_rad))


def _flow_accumulation(dem) -> np.ndarray:
    """
    D8 flow accumulation: for each cell, route flow to the lowest neighbour.
    Returns a 2D array of upstream cell counts.
    """
    rows, cols = dem.shape
    neighbours = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]

    flow_dir = np.full((rows, cols), -1, dtype=int)
    for r in range(1, rows - 1):
        for c in range(1, cols - 1):
            min_elev = dem[r, c]
            best = -1
            for i, (dr, dc) in enumerate(neighbours):
                nr, nc = r + dr, c + dc
                if dem[nr, nc] < min_elev:
                    min_elev = dem[nr, nc]
                    best = i
            flow_dir[r, c] = best

    accum = np.ones((rows, cols), dtype=float)
    flat = [(dem[r, c], r, c) for r in range(rows) for c in range(cols)]
    flat.sort(reverse=True)
    for _, r, c in flat:
        d = flow_dir[r, c]
        if d >= 0:
            dr, dc = neighbours[d]
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                accum[nr, nc] += accum[r, c]
    return accum


def _twi(dem, accum, row: int, col: int, cell_size_m: float = 30.0) -> float:
    """Topographic Wetness Index = ln(A / tan(β)), clamped to [0, 15]."""
    slope_rad = np.radians(_slope_degrees(dem, row, col, cell_size_m))
    tan_slope = max(float(np.tan(slope_rad)), 0.001)
    area = float(accum[row, col]) * (cell_size_m ** 2)
    twi_val = np.log(area / tan_slope)
    return round(float(np.clip(twi_val, 0, 15)), 2)


def _distance_to_channel(
    dem, accum, row: int, col: int, cell_size_m: float = 30.0, min_accum: int = 500
) -> float:
    """Returns distance in metres to nearest channel pixel (accum > min_accum)."""
    channel_mask = accum > min_accum
    if not channel_mask.any():
        return 9999.0

    channel_rows, channel_cols = np.where(channel_mask)
    distances = np.sqrt(
        ((channel_rows - row) * cell_size_m) ** 2
        + ((channel_cols - col) * cell_size_m) ** 2
    )
    return float(distances.min())


def _is_floodplain(
    dem, accum, row: int, col: int, cell_size_m: float = 30.0, min_accum: int = 500
) -> bool:
    """True if property is within 1km of a channel AND within 10m elevation of it.

    10m threshold (not 3m) captures raised floodplain terraces typical of
    Romanian rivers, where a property sits 5–15m above the active channel but
    is still inundated when the river overtops its banks.
    """
    channel_mask = accum > min_accum
    if not channel_mask.any():
        return False

    channel_rows, channel_cols = np.where(channel_mask)
    distances = np.sqrt(
        ((channel_rows - row) * cell_size_m) ** 2
        + ((channel_cols - col) * cell_size_m) ** 2
    )
    nearest_idx = distances.argmin()
    nearest_dist_m = distances[nearest_idx]
    nearest_elev = dem[channel_rows[nearest_idx], channel_cols[nearest_idx]]
    prop_elev = dem[row, col]

    return bool(nearest_dist_m < 1000 and (prop_elev - nearest_elev) < 10.0)


def _terrain_flood_score(
    elev_percentile: float,
    twi_val: float,
    dist_to_river: float,
    in_floodplain: bool,
) -> float:
    """Combined terrain flood risk score, 0–1."""
    score = 0.0

    twi_score = min(1.0, max(0.0, (twi_val - 4.0) / (12.0 - 4.0)))
    score += twi_score * 0.40

    elev_score = min(1.0, max(0.0, 1.0 - (elev_percentile / 100.0)))
    score += elev_score * 0.25

    if dist_to_river < 100:
        dist_score = 1.0
    elif dist_to_river < 500:
        dist_score = 0.8
    elif dist_to_river < 1000:
        dist_score = 0.5
    elif dist_to_river < 2000:
        dist_score = 0.2
    else:
        dist_score = 0.0
    score += dist_score * 0.25

    score += 0.10 if in_floodplain else 0.0

    return round(min(1.0, score), 4)


def get_terrain_data(lat: float, lon: float) -> dict:
    """Pull Copernicus 30m DEM for 5km box and compute TWI + terrain flood score."""
    try:
        dem, transform = _fetch_dem(lat, lon, margin_km=5.0)
    except Exception as e:
        print(f"[ERROR] DEM fetch failed: {e}")
        return {
            "elevation_m": 100.0,
            "slope_degrees": 2.0,
            "twi": 6.0,
            "distance_to_river_m": 1000.0,
            "is_in_floodplain": False,
            "elevation_percentile": 50.0,
            "terrain_flood_score": 0.3,
        }

    row, col = _property_cell(dem, transform, lat, lon)
    elev, elev_pct = _elevation_percentile(dem, row, col)
    slope = _slope_degrees(dem, row, col)
    accum = _flow_accumulation(dem)
    twi_val = _twi(dem, accum, row, col)
    dist = _distance_to_channel(dem, accum, row, col)
    in_fp = _is_floodplain(dem, accum, row, col)
    score = _terrain_flood_score(elev_pct, twi_val, dist, in_fp)

    return {
        "elevation_m": round(elev, 1),
        "slope_degrees": round(slope, 2),
        "twi": twi_val,
        "distance_to_river_m": round(dist, 1),
        "is_in_floodplain": in_fp,
        "elevation_percentile": elev_pct,
        "terrain_flood_score": score,
    }
