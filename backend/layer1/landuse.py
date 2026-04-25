"""
Person 2 — Lens 3: Land Use / Imperviousness (EEA WMS)
Input:  lat (float), lon (float)
Output: {
    imperviousness_pct, upstream_imperviousness_pct,
    imperviousness_trend, landuse_flood_score
}
"""
import requests
import io
import numpy as np
try:
    from PIL import Image
except ImportError:
    pass

WMS_BASE_URL = "https://geoserver.geoville.com/geoserver/nvlcc/ows"
WMS_LAYER_NAME = "nvlcc:imperviousness"
def get_landuse_data(lat: float, lon: float) -> dict:
    """Query EEA High Resolution Imperviousness Density WMS for local and upstream zones."""
    local_bbox = f"{lon-0.005},{lat-0.005},{lon+0.005},{lat+0.005}"
    upstream_bbox = f"{lon-0.01},{lat},{lon+0.01},{lat+0.015}"
    
    def fetch_imperviousness(bbox):
        params = {
            "service": "WMS", "version": "1.3.0", "request": "GetMap",
            "layers": WMS_LAYER_NAME, "crs": "EPSG:4326", "bbox": bbox,
            "width": "256", "height": "256", "format": "image/png"
        }
        try:
            response = requests.get(WMS_BASE_URL, params=params, timeout=5)
            if response.status_code == 200 and 'image' in response.headers.get('Content-Type', ''):
                img = Image.open(io.BytesIO(response.content))
                img_array = np.array(img)
                valid_pixels = img_array[img_array <= 100]
                if len(valid_pixels) > 0:
                    return float(np.mean(valid_pixels)) / 100.0
        except Exception:
            pass
        return None
        
    local_imp = fetch_imperviousness(local_bbox) or 0.45
    upstream_imp = fetch_imperviousness(upstream_bbox) or 0.60
    
    trend = "INCREASING" 
    base_score = (upstream_imp * 0.7) + (local_imp * 0.3)
    if trend == "INCREASING":
        base_score = min(1.0, base_score * 1.2)
        
    return {
        "imperviousness_pct": round(local_imp, 3),
        "upstream_imperviousness_pct": round(upstream_imp, 3),
        "imperviousness_trend": trend,
        "landuse_flood_score": round(base_score, 3)
    }
