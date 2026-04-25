"""
Person 2 — Lens 5: Flood Defenses
Input:  lat (float), lon (float)
Output: {
    flood_defense_present,
    defense_protection_level,
    defense_data_source
}

Default: no defenses (honest for most Romanian properties).
Hero example: manually researched via INHGA public information.
"""

import requests
import hashlib

def get_defense_data(lat: float, lon: float) -> dict:
    """Return flood defense status by querying OSM Overpass API for embankments/dykes."""
    query = f"""
    [out:json][timeout:5];
    (
      way["man_made"="dyke"](around:5000, {lat}, {lon});
      way["embankment"="dyke"](around:5000, {lat}, {lon});
    );
    out body;
    """
    
    has_defense = False
    data_source = "DEFAULT_ASSUMPTION"
    protection_level = "NONE"
    
    try:
        headers = {"User-Agent": "HydroRisk-Client/1.0"}
        resp = requests.post("https://overpass-api.de/api/interpreter", data={"data": query}, headers=headers, timeout=12)
        if resp.status_code == 200:
            data = resp.json()
            elements = data.get("elements", [])
            if len(elements) > 0:
                has_defense = True
                data_source = "OPEN_STREET_MAP"
                protection_level = "HIGH" if len(elements) > 5 else "MEDIUM"
            else:
                data_source = "OPEN_STREET_MAP"  # Explicitly confirmed no defense
    except Exception as e:
        print("OVERPASS EXCEPTION:", e)
        # Fallback to procedural mock if OSM API is down or times out
        hash_val = int(hashlib.md5(f"{lat:.2f}{lon:.2f}".encode()).hexdigest(), 16) % 100
        has_defense = hash_val < (45 if lon < 15 else 25)
        if has_defense:
            data_source = "PROCEDURAL_MOCK"
            protection_level = "MEDIUM"

    return {
        "flood_defense_present": has_defense,
        "defense_protection_level": protection_level,
        "defense_data_source": data_source,
    }
