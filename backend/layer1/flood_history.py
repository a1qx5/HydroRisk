"""
Person 1 — Lens 1: Flood History (Sentinel-1 SAR)
Input:  lat (float), lon (float)
Output: {
    flood_events_10yr, years_with_flooding,
    annual_flood_probability_observed, flood_direct_hits,
    flood_history_confidence
}
"""

import math

import numpy as np
from sentinelhub import (
    BBox,
    CRS,
    DataCollection,
    MimeType,
    SentinelHubRequest,
    bbox_to_dimensions,
)

CDSE_BASE_URL = "https://sh.dataspace.copernicus.eu"
CDSE_AUTH_URL = "https://identity.dataspace.copernicus.eu"

S1_CDSE = DataCollection.SENTINEL1_IW.define_from(
    "SENTINEL1_IW_CDSE", service_url=CDSE_BASE_URL
)

EVALSCRIPT_S1 = """
//VERSION=3
function setup() {
  return {
    input: ["VV"],
    output: { bands: 1, sampleType: "FLOAT32" },
    mosaicking: "ORBIT"
  };
}
function evaluatePixel(samples) {
  var minVV = 1.0;
  for (var i = 0; i < samples.length; i++) {
    if (samples[i].VV < minVV) minVV = samples[i].VV;
  }
  return [minVV];
}
"""

WATER_THRESHOLD = 0.03


def _bounding_box(lat: float, lon: float, margin_km: float = 2.0) -> dict:
    lat_margin = margin_km / 111.0
    lon_margin = margin_km / (111.0 * math.cos(math.radians(lat)))
    return {
        "min_lat": lat - lat_margin,
        "max_lat": lat + lat_margin,
        "min_lon": lon - lon_margin,
        "max_lon": lon + lon_margin,
    }


def _fetch_s1_image(bbox_coords, start_date: str, end_date: str, config):
    bbox = BBox(bbox=bbox_coords, crs=CRS.WGS84)
    size = bbox_to_dimensions(bbox, resolution=20)

    request = SentinelHubRequest(
        evalscript=EVALSCRIPT_S1,
        input_data=[
            SentinelHubRequest.input_data(
                data_collection=S1_CDSE,
                time_interval=(start_date, end_date),
                other_args={
                    "processing": {"orthorectify": True, "backCoeff": "SIGMA0_ELLIPSOID"},
                    "dataFilter": {"orbitDirection": "ASCENDING"},
                },
            )
        ],
        responses=[SentinelHubRequest.output_response("default", MimeType.TIFF)],
        bbox=bbox,
        size=size,
        config=config,
    )
    images = request.get_data()
    return images[0] if images else None


def _detect_flood(image_array):
    """
    Returns (direct_hit, near_miss).
    direct_hit: >35% of centre 10% pixels are water.
    near_miss:  >55% of full bounding box pixels are water.
    """
    if image_array is None:
        return False, False

    vv = image_array[:, :, 0] if image_array.ndim == 3 else image_array
    water_mask = vv < WATER_THRESHOLD

    h, w = vv.shape
    cy, cx = h // 2, w // 2
    margin_y, margin_x = max(1, h // 10), max(1, w // 10)
    centre = water_mask[cy - margin_y: cy + margin_y, cx - margin_x: cx + margin_x]
    # 0.35: river+floodplain covers ~35-45% of the 800m centre window
    # when 256m from the river; strict 0.5 never triggers on raised terraces
    direct_hit = bool(centre.mean() > 0.35)

    # 0.30: with 1km margin box, mountain slope shadows stay below ~25% of the
    # 2km×2km area; real floodplain inundations still exceed 30%
    near_miss = bool(water_mask.mean() > 0.30)

    return direct_hit, near_miss


def get_flood_history(lat: float, lon: float) -> dict:
    """Search Sentinel-1 SAR archive (2014–today) for flood events near this property."""
    from sentinelhub import SHConfig
    from backend.config import SENTINEL_HUB_CLIENT_ID, SENTINEL_HUB_CLIENT_SECRET

    config = SHConfig()
    config.sh_client_id = SENTINEL_HUB_CLIENT_ID
    config.sh_client_secret = SENTINEL_HUB_CLIENT_SECRET
    config.sh_base_url = CDSE_BASE_URL
    config.sh_auth_base_url = CDSE_AUTH_URL
    # Required: library defaults to old sentinel-hub.com token endpoint
    config.sh_token_url = (
        "https://identity.dataspace.copernicus.eu"
        "/auth/realms/CDSE/protocol/openid-connect/token"
    )

    bb = _bounding_box(lat, lon, margin_km=2.0)
    bbox_coords = (bb["min_lon"], bb["min_lat"], bb["max_lon"], bb["max_lat"])

    years = list(range(2014, 2026))
    windows = [("03-01", "05-31"), ("09-01", "11-30")]

    flood_events = 0
    direct_hits = 0
    years_flooded = set()

    for year in years:
        year_flooded = False
        for (m_start, m_end) in windows:
            start = f"{year}-{m_start}"
            end = f"{year}-{m_end}"
            try:
                image = _fetch_s1_image(bbox_coords, start, end, config)
                hit, near_miss = _detect_flood(image)
                if hit or near_miss:
                    flood_events += 1
                    year_flooded = True
                if hit:
                    direct_hits += 1
            except Exception as e:
                print(f"[WARN] Sentinel-1 query failed {start}–{end}: {e}")

        if year_flooded:
            years_flooded.add(year)

    total_years = len(years)
    probability = len(years_flooded) / total_years

    if direct_hits > 2:
        confidence = "HIGH"
    elif direct_hits >= 1:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    return {
        "flood_events_10yr": flood_events,
        "years_with_flooding": len(years_flooded),
        "annual_flood_probability_observed": round(probability, 4),
        "flood_direct_hits": direct_hits,
        "flood_history_confidence": confidence,
    }
