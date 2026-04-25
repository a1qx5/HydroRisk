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


def _fill_depressions(work: np.ndarray, passes: int = 5) -> np.ndarray:
    """
    Fill local pits by raising cells that are lower than all 8 neighbours.
    Operates on a NoData-free surface (NoData already replaced with a high sentinel).
    Pure-numpy, vectorised — runs in milliseconds on a 333×333 grid.
    """
    for _ in range(passes):
        h, w = work.shape
        nm = np.full((h, w), np.inf)
        nm[1:,  :]   = np.minimum(nm[1:,  :],   work[:-1, :])    # north
        nm[:-1, :]   = np.minimum(nm[:-1, :],   work[1:,  :])    # south
        nm[:,  1:]   = np.minimum(nm[:,  1:],    work[:,  :-1])   # west
        nm[:, :-1]   = np.minimum(nm[:, :-1],    work[:,  1:])    # east
        nm[1:,  1:]  = np.minimum(nm[1:,  1:],   work[:-1, :-1]) # NW
        nm[:-1, 1:]  = np.minimum(nm[:-1, 1:],   work[1:,  :-1]) # SW
        nm[1:, :-1]  = np.minimum(nm[1:, :-1],   work[:-1, 1:])  # NE
        nm[:-1, :-1] = np.minimum(nm[:-1, :-1],  work[1:,  1:])  # SE
        work = np.where(work < nm, nm, work)
    return work


def _flow_accumulation(dem) -> np.ndarray:
    """
    D8 flow accumulation: for each cell, route flow to the lowest neighbour.
    Returns a 2D array of upstream cell counts.
    Depressions are filled before routing so flow reaches river channels.
    """
    rows, cols = dem.shape
    neighbours = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]

    # Build routing surface: NoData → impassable high ground, then fill pits
    valid = dem > -9000
    work = dem.copy().astype(np.float64)
    if valid.any():
        work[~valid] = float(work[valid].max()) + 1.0
    work = _fill_depressions(work)

    flow_dir = np.full((rows, cols), -1, dtype=int)
    for r in range(1, rows - 1):
        for c in range(1, cols - 1):
            min_elev = work[r, c]
            best = -1
            for i, (dr, dc) in enumerate(neighbours):
                nr, nc = r + dr, c + dc
                if work[nr, nc] < min_elev:
                    min_elev = work[nr, nc]
                    best = i
            flow_dir[r, c] = best

    accum = np.where(valid, 1.0, 0.0)
    flat = [(work[r, c], r, c) for r in range(rows) for c in range(cols)]
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



def _point_to_segment_m(plat: float, plon: float, alat: float, alon: float, blat: float, blon: float):
    """
    Distance in metres from point P to segment AB, plus coordinates of the nearest point.
    Uses a local Euclidean projection (error < 0.1% for segments under 5 km).
    Returns (distance_m, nearest_lat, nearest_lon).
    """
    cos_lat = math.cos(math.radians(plat))
    sx = 111_000.0 * cos_lat  # m per degree lon at this latitude
    sy = 111_000.0             # m per degree lat

    px = (plon - alon) * sx
    py = (plat - alat) * sy
    bx = (blon - alon) * sx
    by = (blat - alat) * sy

    seg_sq = bx * bx + by * by
    t = max(0.0, min(1.0, (px * bx + py * by) / seg_sq)) if seg_sq > 1e-10 else 0.0

    dx = px - t * bx
    dy = py - t * by
    return math.sqrt(dx * dx + dy * dy), alat + t * (blat - alat), alon + t * (blon - alon)


def _nearest_waterway_osm(lat: float, lon: float, radius_m: float = 5000):
    """
    Query OSM Overpass for the nearest point on any river/stream/canal segment.
    Returns (distance_m, nearest_lat, nearest_lon).
    Falls back to (9999.0, lat, lon) on network failure or no result.

    COP30 is a DSM that cannot reliably detect channels in urban / flat terrain.
    OSM waterway data is authoritative and requires no API key.
    """
    query = (
        f"[out:json][timeout:15];"
        f"("
        f'way["waterway"="river"](around:{radius_m},{lat},{lon});'
        f'way["waterway"="stream"](around:{radius_m},{lat},{lon});'
        f'way["waterway"="canal"](around:{radius_m},{lat},{lon});'
        f");"
        f"(._;>;);"
        f"out body;"
    )
    try:
        resp = requests.post(
            "https://overpass-api.de/api/interpreter",
            data={"data": query},
            headers={"User-Agent": "HydroRisk/1.0 (flood-risk scoring)"},
            timeout=20,
        )
        resp.raise_for_status()
        elements = resp.json().get("elements", [])
        nodes = {
            e["id"]: (e["lat"], e["lon"])
            for e in elements
            if e["type"] == "node" and "lat" in e
        }
        ways = [e for e in elements if e["type"] == "way"]
        if not nodes or not ways:
            print(f"[WARN] OSM: no waterway data near ({lat:.4f}, {lon:.4f})")
            return 9999.0, lat, lon
        best_dist, best_lat, best_lon = 9999.0, lat, lon
        for way in ways:
            node_ids = way.get("nodes", [])
            for i in range(len(node_ids) - 1):
                a = nodes.get(node_ids[i])
                b = nodes.get(node_ids[i + 1])
                if a is None or b is None:
                    continue
                d, nlat, nlon = _point_to_segment_m(lat, lon, a[0], a[1], b[0], b[1])
                if d < best_dist:
                    best_dist, best_lat, best_lon = d, nlat, nlon
        return round(best_dist, 1), best_lat, best_lon
    except Exception as e:
        print(f"[WARN] OSM waterway query failed for ({lat:.4f}, {lon:.4f}): {e}")
        return 9999.0, lat, lon


def _is_floodplain(
    dem, transform, dist_m: float, waterway_lat: float, waterway_lon: float,
    prop_row: int, prop_col: int,
) -> bool:
    """True if property is within 1km of a waterway AND within 10m elevation of it.

    10m threshold (not 3m) captures raised floodplain terraces typical of
    Romanian rivers, where a property sits 5–15m above the active channel but
    is still inundated when the river overtops its banks.
    """
    if dist_m >= 1000:
        return False
    try:
        w_row, w_col = _property_cell(dem, transform, waterway_lat, waterway_lon)
        waterway_elev = dem[w_row, w_col]
        if waterway_elev <= -9000:
            return dist_m < 500
        prop_elev = dem[prop_row, prop_col]
        return bool((prop_elev - waterway_elev) < 10.0)
    except Exception:
        return dist_m < 500


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
    dist, w_lat, w_lon = _nearest_waterway_osm(lat, lon)
    in_fp = _is_floodplain(dem, transform, dist, w_lat, w_lon, row, col)
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
