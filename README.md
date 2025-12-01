# OSM Czech Republic Dashboard
This project demonstrates how OpenStreetMap (OSM) data can be explored, analyzed, and visualized using a combination of PostgreSQL/PostGIS and Python. The goal is to introduce readers to the idea that OSM is not only a map you browse in a browser, but also a rich, open dataset that can be used for analysis, research, and custom applications.

## Overview
The script downloads OSM data (via Geofabrik), loads it into a PostGIS-enabled PostgreSQL database, runs several analytical queries, and generates an HTML dashboard.
The dashboard includes:

- Basic statistics (nodes, ways, relations, buildings, POIs, roads, etc.)
- Heatmap of selected points of interest
- Charts of common amenities, shops, landuse types, and tourism features
- A short explanation of OSM and how the dataset was prepared

## Features
- Fully local and reproducible process
- No external APIs required
- Simple Python workflow for generating visual outputs
- Demonstrates how GIS data can be queried using SQL and transformed using Python
- Highlights the breadth of information available in OpenStreetMap

## Usage
1. Download ```.osm.pbf``` file for Czech Republic from Geofabrik
2. Create PostGreSQL database and enable PostGIS + HSTORE
3. Import the data using osm2pgsql
4. Run thy Python script to geenrate dashboard (osm_czech_dashboard.html) and heatmap (osm_heatmap.htlm) :
    ```uv run main.py```