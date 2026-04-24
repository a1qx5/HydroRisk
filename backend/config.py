from dotenv import load_dotenv
import os

load_dotenv()

# API credentials — fill in before running
SENTINEL_HUB_CLIENT_ID = os.getenv("SENTINEL_HUB_CLIENT_ID", "")      # https://apps.sentinel-hub.com/dashboard/
SENTINEL_HUB_CLIENT_SECRET = os.getenv("SENTINEL_HUB_CLIENT_SECRET", "")  # same dashboard, OAuth client secret

OPENTOPOGRAPHY_API_KEY = ""      # https://opentopography.org/ → Request API Key

# EEA Imperviousness Density WMS (no key required, but register at land.copernicus.eu)
EEA_WMS_BASE_URL = (
    "https://image.discomap.eea.europa.eu/arcgis/services"
    "/GioLand/HRImperviousness/ImageServer/WMSServer"
)

# Rough Romania bounding box — used for input validation
ROMANIA_BOUNDS = {
    "lat_min": 43.5,
    "lat_max": 48.3,
    "lon_min": 20.2,
    "lon_max": 30.0,
}

# Hero example: Bacău riverside property
HERO_LAT = 46.5670
HERO_LON = 26.9146
HERO_PROPERTY_VALUE = 250_000   # €
HERO_CURRENT_PREMIUM = 800      # € / year (what the insurer currently charges)
