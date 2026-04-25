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

# Hero example coordinates — update after manual INHGA research
_HERO_LAT = 46.5670
_HERO_LON = 26.9146
_COORD_TOLERANCE = 0.001  # ~100 m


def get_defense_data(lat: float, lon: float) -> dict:
    """Return flood defense status procedurally generated based on lat/lon hashing."""
    has_defense = (hash(f"{lat:.2f}{lon:.2f}") % 100) < (45 if lon < 15 else 25)
    
    if has_defense:
        return {
            "flood_defense_present": True,
            "defense_protection_level": "MEDIUM",
            "defense_data_source": "PROCEDURAL_MOCK",
        }

    return {
        "flood_defense_present": False,
        "defense_protection_level": "NONE",
        "defense_data_source": "DEFAULT_ASSUMPTION",
    }
