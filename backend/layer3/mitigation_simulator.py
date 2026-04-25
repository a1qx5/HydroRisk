"""
Layer 3 — Mitigation Simulator
Input:  property_data dict (from get_property_data or cached raw_property_data)
        geometries: list of GeoJSON Feature dicts
          - LineString → flood barrier
          - Polygon    → retention basin
Output: {
    adjusted_property_data,  # modified copy — originals untouched
    mitigation_effects,      # human-readable explanation of each change
}
"""

import math


# ── Geometry helpers ──────────────────────────────────────────────────────────

def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance in metres between two WGS84 points."""
    R = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _point_to_segment_dist_m(plat, plon, alat, alon, blat, blon) -> float:
    """Shortest distance in metres from point P to line segment AB."""
    # Project onto local Euclidean plane
    cos_lat = math.cos(math.radians(plat))
    sx = 111_000.0 * cos_lat
    sy = 111_000.0

    px = (plon - alon) * sx
    py = (plat - alat) * sy
    bx = (blon - alon) * sx
    by = (blat - alat) * sy

    seg_sq = bx * bx + by * by
    t = max(0.0, min(1.0, (px * bx + py * by) / seg_sq)) if seg_sq > 1e-10 else 0.0
    dx = px - t * bx
    dy = py - t * by
    return math.sqrt(dx * dx + dy * dy)


def _polyline_length_m(coords: list) -> float:
    """Total length of a polyline (list of [lon, lat] pairs) in metres."""
    total = 0.0
    for i in range(len(coords) - 1):
        total += _haversine_m(coords[i][1], coords[i][0], coords[i + 1][1], coords[i + 1][0])
    return total


def _min_dist_to_line_m(lat: float, lon: float, coords: list) -> float:
    """Minimum distance in metres from point to any segment of a polyline."""
    best = float("inf")
    for i in range(len(coords) - 1):
        a, b = coords[i], coords[i + 1]
        d = _point_to_segment_dist_m(lat, lon, a[1], a[0], b[1], b[0])
        if d < best:
            best = d
    return best


def _polygon_area_m2(coords: list) -> float:
    """
    Approximate area of a GeoJSON polygon ring (list of [lon, lat]) in m².
    Uses the shoelace formula on a local Euclidean projection.
    """
    if not coords:
        return 0.0
    cx = sum(c[0] for c in coords) / len(coords)
    cy = sum(c[1] for c in coords) / len(coords)
    cos_lat = math.cos(math.radians(cy))
    sx = 111_000.0 * cos_lat
    sy = 111_000.0

    xs = [(c[0] - cx) * sx for c in coords]
    ys = [(c[1] - cy) * sy for c in coords]
    area = 0.0
    n = len(xs)
    for i in range(n):
        j = (i + 1) % n
        area += xs[i] * ys[j]
        area -= xs[j] * ys[i]
    return abs(area) / 2.0


def _polygon_centroid(coords: list) -> tuple:
    """Centroid (lat, lon) of a polygon ring."""
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return sum(lats) / len(lats), sum(lons) / len(lons)


# ── Score adjusters ───────────────────────────────────────────────────────────

_BARRIER_RADIUS_M   = 2_000   # barrier must be within this distance to count
_BASIN_RADIUS_M     = 2_000   # basin centroid must be within this distance
_BASIN_MIN_AREA_M2  = 5_000   # minimum basin area to count


def _apply_barrier(data: dict, coords: list, effects: list) -> dict:
    """Adjust defense score based on a drawn flood barrier (LineString)."""
    min_dist = _min_dist_to_line_m(data["lat"], data["lon"], coords)
    if min_dist > _BARRIER_RADIUS_M:
        effects.append(f"Barrier ignored — furthest than {_BARRIER_RADIUS_M}m from property.")
        return data

    length_m = _polyline_length_m(coords)

    if length_m >= 500:
        level = "HIGH"
    elif length_m >= 200:
        level = "MEDIUM"
    else:
        level = "LOW"

    old_present = data.get("flood_defense_present", False)
    old_level   = data.get("defense_protection_level", "NONE")

    # Only upgrade, never downgrade
    _rank = {"NONE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}
    if _rank[level] > _rank.get(old_level, 0):
        data = dict(data)
        data["flood_defense_present"]    = True
        data["defense_protection_level"] = level
        effects.append(
            f"Barrier ({length_m:.0f}m, {min_dist:.0f}m from property): "
            f"defense upgraded {old_level} → {level}."
        )
    else:
        effects.append(
            f"Barrier ({length_m:.0f}m): already at {old_level}, no upgrade."
        )
    return data


def _apply_basin(data: dict, coords: list, effects: list) -> dict:
    """Adjust terrain score based on a drawn retention basin (Polygon)."""
    clat, clon = _polygon_centroid(coords)
    dist_m = _haversine_m(data["lat"], data["lon"], clat, clon)

    if dist_m > _BASIN_RADIUS_M:
        effects.append(f"Basin ignored — centroid {dist_m:.0f}m away (>{_BASIN_RADIUS_M}m).")
        return data

    area_m2 = _polygon_area_m2(coords)
    if area_m2 < _BASIN_MIN_AREA_M2:
        effects.append(f"Basin ignored — area {area_m2:.0f}m² (< {_BASIN_MIN_AREA_M2}m² minimum).")
        return data

    # Reduction: 0.10 for 5,000 m², scales linearly up to 0.25 at 50,000+ m²
    reduction = min(0.25, 0.10 + (area_m2 - _BASIN_MIN_AREA_M2) / 450_000)
    old_score = data.get("terrain_flood_score", 0.3)
    new_score = max(0.0, old_score - reduction)

    data = dict(data)
    data["terrain_flood_score"] = round(new_score, 4)
    # Also reflect in is_in_floodplain if score drops below moderate threshold
    if new_score < 0.35 and data.get("is_in_floodplain"):
        data["is_in_floodplain"] = False
        effects.append(
            f"Basin ({area_m2:.0f}m², {dist_m:.0f}m away): "
            f"terrain score {old_score:.3f} → {new_score:.3f}; floodplain status lifted."
        )
    else:
        effects.append(
            f"Basin ({area_m2:.0f}m², {dist_m:.0f}m away): "
            f"terrain score {old_score:.3f} → {new_score:.3f}."
        )
    return data


# ── Public API ────────────────────────────────────────────────────────────────

def simulate_mitigation(property_data: dict, geometries: list) -> dict:
    """
    Apply user-drawn geometries to property_data and return adjusted copy.

    Args:
        property_data: dict from get_property_data() or raw_property_data cache
        geometries:    list of GeoJSON Feature dicts

    Returns:
        {
            "adjusted_property_data": dict,
            "mitigation_effects":     list[str],
        }
    """
    data    = dict(property_data)   # shallow copy — values not mutated in place
    effects = []

    for feature in geometries:
        geom = feature.get("geometry", {})
        gtype = geom.get("type", "")
        coords = geom.get("coordinates", [])

        if gtype == "LineString" and len(coords) >= 2:
            data = _apply_barrier(data, coords, effects)

        elif gtype == "Polygon" and coords:
            # GeoJSON Polygon: coords[0] is outer ring
            data = _apply_basin(data, coords[0], effects)

    if not effects:
        effects.append("No valid mitigation geometries found within range.")

    return {
        "adjusted_property_data": data,
        "mitigation_effects":     effects,
    }
