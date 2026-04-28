HydroRisk - Flood Risk Intelligence

HydroRisk is a satellite-driven flood risk assessment platform developed for the Cassini Hackathon. It utilizes European space data (Sentinel-1, Copernicus DEM, and C3S) to provide insurers and property owners with precise, real-time flood probability and financial risk analysis.

The platform addresses the gap in flood insurance by replacing static, outdated maps with a dynamic "5-Lens" analysis model. It allows users to assess individual properties or entire portfolios to identify mispriced risks and simulate the impact of flood mitigation infrastructure.
Key Features

    Property Risk Assessment: Analyze any property by address or coordinates using high-resolution satellite telemetry.

    The 5-Lens Risk Engine:

        Flood History: 12-year archive analysis using Sentinel-1 SAR imagery.

        Terrain Analysis: 30m resolution elevation and slope data from Copernicus DEM.

        Land Use: Real-time soil imperviousness data from the EEA High Resolution Layer.

        Climate Projections: Regional precipitation trends projected to 2035 using C3S models.

        Defenses: Mapping of existing flood barriers and embankments via OpenStreetMap.

    Mitigation Designer: An interactive tool to draw flood barriers or retention basins on a map to visualize immediate reductions in risk and insurance premiums.

    Portfolio Simulator: A financial modeling tool for insurers to calculate the ROI of adopting HydroRisk across their book of business.

    Accumulation Scan: Identifies geographic clusters where high-risk policies are concentrated.

    Intelligence Dossier: Export comprehensive PDF risk reports for internal underwriting or property valuation.

Technology Stack
Backend

    Language: Python 3.x

    Framework: Flask

    Geospatial Libraries: Rasterio, NumPy, SciPy, SentinelHub API

    Data Sources: Sentinel-1 SAR, Copernicus DEM 30m (GLO-30), EEA High Resolution Imperviousness Density

Frontend

    Core: HTML5, CSS3, JavaScript

    Mapping: Leaflet.js, Leaflet.draw

    Reporting: html2pdf

Getting Started
1. Environment Setup

Create a .env file in the root directory and add your API credentials:
Fragment de cod

SENTINEL_HUB_CLIENT_ID="your_client_id"
SENTINEL_HUB_CLIENT_SECRET="your_client_secret"
OPENTOPOGRAPHY_API_KEY="your_api_key"

2. Install Dependencies

Run the provided installer script to manage environment-specific dependencies:
Bash

python install_deps.py

3. Running the Application

Start the Backend API:
Bash

cd backend
python api.py

Start the Frontend:
Bash

cd frontend
python -m http.server 8000

The application will be accessible at http://localhost:8000.
Methodology and Validation

The HydroRisk weighted model is validated against historical flood insurance claims data. The platform’s premium recommendations utilize the JRC European Flood Depth-Damage Curves, ensuring actuarial alignment with EU benchmarks. The core risk engine weights factors based on empirical analysis, where satellite flood history and terrain are identified as the primary predictors of severe loss.
