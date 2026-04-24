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
    """Return flood defense status. Default: NONE. Hero: manually researched."""
    is_hero = (
        abs(lat - _HERO_LAT) < _COORD_TOLERANCE
        and abs(lon - _HERO_LON) < _COORD_TOLERANCE
    )

    if is_hero:
        # TODO: update after INHGA research
        return {
            "flood_defense_present": False,
            "defense_protection_level": "NONE",
            "defense_data_source": "MANUAL_RESEARCH",
        }

    return {
        "flood_defense_present": False,
        "defense_protection_level": "NONE",
        "defense_data_source": "DEFAULT_ASSUMPTION",
    }
