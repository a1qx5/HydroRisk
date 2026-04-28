HydroRisk - Flood Risk Intelligence

HydroRisk is a high-fidelity flood risk assessment platform developed for the Cassini Hackathon. The system integrates European space data, including Sentinel-1 SAR imagery, Copernicus Digital Elevation Models (DEM), and Copernicus Climate Change Service (C3S) projections, to provide insurers and property owners with dynamic flood probability and financial risk analysis.

By shifting from static, historical flood maps to a dynamic "5-Lens" predictive model, the platform identifies mispriced risks and allows for the simulation of flood mitigation infrastructure impacts.
Key Features

    Property Risk Assessment: Evaluate specific locations via address or coordinate input using high-resolution satellite telemetry.

    Interactive Mitigation Designer: A geospatial tool allowing users to "draw" flood barriers or retention basins directly on the map to visualize real-time risk reduction and premium adjustments.

    Portfolio Management: Financial modeling tools for insurance providers to assess risk across large property books and calculate the ROI of mitigation efforts.

    Accumulation Analysis: Automated detection of geographic risk clusters where high-exposure policies are concentrated within shared hydrological catchments.

    Dossier Generation: Export automated PDF risk reports containing detailed scoring and environmental data for underwriting and valuation.

The 5-Lens Risk Engine

The HydroRisk core engine synthesizes five distinct data layers to generate a comprehensive risk score:

    Flood History: Analysis of 12 years of archival Sentinel-1 SAR imagery to detect historical inundation patterns.

    Terrain Analysis: Slope and elevation modeling derived from 30m resolution Copernicus DEM (GLO-30) data.

    Land Use: Soil imperviousness and surface permeability data sourced from the EEA High Resolution Layer.

    Climate Projections: Predictive precipitation and climate trend modeling extending to 2035 using C3S datasets.

    Defense Infrastructure: Real-time mapping of existing barriers, embankments, and flood-control structures via OpenStreetMap.

Technical Architecture
Backend Stack

    Environment: Python 3.x

    API Framework: Flask

    Geospatial Processing: Rasterio, NumPy, SciPy, SentinelHub API

    Data Pipelines: Automated retrieval from Copernicus Data Space Ecosystem and OpenTopography

Frontend Stack

    Interface: HTML5 / CSS3 with a Glassmorphism UI design

    Mapping Engine: Leaflet.js and Leaflet.draw for geospatial interactions

    Export Engine: html2pdf for automated reporting

Installation and Setup
1. Environment Configuration

Create a .env file in the project root directory. You will need to provide credentials for the following services:
Plaintext

SENTINEL_HUB_CLIENT_ID="your_client_id"
SENTINEL_HUB_CLIENT_SECRET="your_client_secret"
OPENTOPOGRAPHY_API_KEY="your_api_key"

2. Dependency Management

To ensure all geospatial libraries and file-system requirements are handled correctly, run the custom installer:
Bash

python install_deps.py

3. Application Execution

Launch the Backend Service:
Bash

cd backend
python api.py

Launch the Frontend Client:
Bash

cd frontend
python -m http.server 8000

The application will be accessible via your browser at http://localhost:8000.
Methodology and Validation

The HydroRisk weighted model is built upon the JRC European Flood Depth-Damage Curves, ensuring premium calculations align with established EU actuarial standards. The model has been validated against historical loss data, identifying satellite-verified flood history and terrain slope as the two most significant predictors of high-severity insurance claims.
License

Developed for the Cassini Hackathon. All rights reserved.
