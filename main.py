import folium
from folium.plugins import HeatMap
import pandas as pd
import matplotlib.pyplot as plt
from sqlalchemy import create_engine, text
import base64
from io import BytesIO

# PLEASE bear in mind that this was done in about an hour and was never meant to be production quality code.
# It is a quick and dirty script to generate a dashboard from OSM data in PostgreSQL

def run_query(engine, query, default=None, fetch_type='scalar'):
    """Helper function to run a query with proper error handling"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query))
            if fetch_type == 'scalar':
                return result.scalar() or default
            elif fetch_type == 'fetchone':
                return result.fetchone() or default
            elif fetch_type == 'fetchall':
                return result.fetchall() or default
    except Exception as e:
        print(f"Query failed: {e}")
        return default

def create_osm_dashboard():
    # Database connection
    engine = create_engine("postgresql://postgres:postgres@localhost/osmcz")
    
    # Create a comprehensive HTML report
    html_content = []
    html_content.append("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>OSM Czech Republic - Data Analytics Dashboard</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: #333;
            }
            .dashboard {
                max-width: 1400px;
                margin: 0 auto;
            }
            .header {
                background: white;
                padding: 30px;
                border-radius: 15px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                margin-bottom: 20px;
                text-align: center;
            }
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 20px;
            }
            .stat-card {
                background: white;
                padding: 25px;
                border-radius: 12px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
                text-align: center;
                transition: transform 0.3s ease;
            }
            .stat-card:hover {
                transform: translateY(-5px);
            }
            .stat-number {
                font-size: 2.5em;
                font-weight: bold;
                color: #667eea;
                margin: 10px 0;
            }
            .stat-label {
                font-size: 0.9em;
                color: #666;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            .visualization {
                background: white;
                padding: 25px;
                border-radius: 15px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                margin-bottom: 20px;
            }
            .section-title {
                color: #2c3e50;
                border-bottom: 3px solid #667eea;
                padding-bottom: 10px;
                margin-bottom: 20px;
            }
            .map-container {
                height: 650px;
                border-radius: 10px;
                overflow: hidden;
                border: 1px solid #ddd;
            }
            .chart-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
            }
            .chart-container {
                text-align: center;
            }
            .insight-box {
                background: linear-gradient(135deg, #667eea, #764ba2);
                color: white;
                padding: 20px;
                border-radius: 12px;
                margin: 20px 0;
            }
        </style>
    </head>
    <body>
        <div class="dashboard">
            <div class="header">
                <h1>🌍 OSM Czech Republic - Data Analytics Dashboard</h1>
                <p>Comprehensive analysis of OpenStreetMap data for Czech Republic</p>
            </div>
    """)
    
    # Get basic statistics
    print("Fetching basic statistics...")
    
    total_nodes = run_query(engine, "SELECT COUNT(*) FROM planet_osm_nodes", 0)
    total_ways = run_query(engine, "SELECT COUNT(*) FROM planet_osm_ways", 0)
    total_relations = run_query(engine, "SELECT COUNT(*) FROM planet_osm_rels", 0)
    
    pois = run_query(engine, """
        SELECT COUNT(*) 
        FROM planet_osm_point 
        WHERE amenity IS NOT NULL 
        OR shop IS NOT NULL 
        OR tourism IS NOT NULL
    """, 0)
    
    buildings = run_query(engine, """
        SELECT COUNT(*) 
        FROM planet_osm_polygon 
        WHERE building IS NOT NULL
    """, 0)
    
    roads_count = run_query(engine, """
        SELECT COUNT(*) 
        FROM planet_osm_roads 
        WHERE highway IS NOT NULL
    """, 0)
    
    amenities = run_query(engine, """
        SELECT amenity, COUNT(*) as count 
        FROM planet_osm_point 
        WHERE amenity IS NOT NULL 
        GROUP BY amenity 
        ORDER BY count DESC 
        LIMIT 10
    """, [], 'fetchall')
    
    shops = run_query(engine, """
        SELECT shop, COUNT(*) as count 
        FROM planet_osm_point 
        WHERE shop IS NOT NULL 
        GROUP BY shop 
        ORDER BY count DESC 
        LIMIT 10
    """, [], 'fetchall')
    
    amenity_types = run_query(engine, """SELECT COUNT(DISTINCT amenity) FROM planet_osm_point WHERE amenity IS NOT NULL;""")
    landuse_types = run_query(engine, """SELECT COUNT(DISTINCT landuse) FROM planet_osm_polygon WHERE landuse IS NOT NULL;""")
    
    # Get coordinate system information
    srid_info = run_query(engine, """
        SELECT DISTINCT ST_SRID(way) as srid 
        FROM planet_osm_point 
        WHERE way IS NOT NULL 
        LIMIT 1
    """, "Unknown")
    
    print(f"Database SRID: {srid_info}")
    
    print("Fetching heatmap data...")
    # Get sample points for heatmap
    heatmap_data = run_query(engine, """
        SELECT ST_X(ST_Transform(way, 4326)) as lon, ST_Y(ST_Transform(way, 4326)) as lat 
        FROM planet_osm_point 
        WHERE (amenity IN ('cafe', 'restaurant', 'pub', 'bar', 'fast_food')
               OR shop IN ('supermarket', 'convenience', 'bakery'))
        AND way IS NOT NULL
    """, [], 'fetchall')
    
    html_content.append('<div class="visualization">')
    html_content.append('<h2 class="section-title">❓ What even is OSM ?</h2>')
    html_content.append('<b>OSM (Open Street Map)</b> is a collaborative project to create a <b>free</b>, <b>editable</b> and <b>open-source</b>  map of the world. Instead of relying on commercial or government sources, people around the world contribute data by drawing roads, buildings, and adding points of interest using GPS devices, aerial imagery, and local knowledge. This collective effort makes OSM a constantly updated, detailed, and highly accurate map that anyone can use for any purpose, from viewing maps online to powering navigation apps.')
    html_content.append('</div>')
    
    
    # Add statistics cards
    html_content.append("""
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Total Nodes</div>
                <div class="stat-number">{:,}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total Ways</div>
                <div class="stat-number">{:,}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total Relations</div>
                <div class="stat-number">{:,}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Points of Interest</div>
                <div class="stat-number">{:,}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Buildings</div>
                <div class="stat-number">{:,}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Road Segments</div>
                <div class="stat-number">{:,}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Amenity Types</div>
                <div class="stat-number">{:,}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Landuse Types</div>
                <div class="stat-number">{:,}</div>
            </div>
        </div>
    """.format(total_nodes, total_ways, total_relations, pois, buildings, roads_count, amenity_types, landuse_types))

    # Create and add heatmap - SIMPLIFIED APPROACH
    print("Creating heatmap visualization...")
    html_content.append('<div class="visualization">')
    html_content.append('<h2 class="section-title">📍 Points of Interest Heatmap</h2>')
    
    if heatmap_data:
        print(f"Processing {len(heatmap_data)} points for heatmap...")
        
        # Filter out None values and ensure valid coordinates
        valid_heat_data = []
        for point in heatmap_data:
            if point and len(point) == 2:
                lon, lat = point
                if (lon is not None and lat is not None and 
                    -180 <= lon <= 180 and -90 <= lat <= 90):
                    valid_heat_data.append([lat, lon])
        
        print(f"Valid points for heatmap: {len(valid_heat_data)}")
        
        if valid_heat_data:
            # Create a standalone map file
            map_filename = 'osm_heatmap.html'
            
            # Create Folium map
            m = folium.Map(
                location=[49.8175, 15.4730], 
                zoom_start=7, 
                tiles='CartoDB positron'
            )
            
            # Add heatmap
            HeatMap(
                valid_heat_data, 
                radius=15, 
                blur=10, 
                gradient={0.4: 'blue', 0.65: 'lime', 1: 'red'}
            ).add_to(m)
            
            # Save as standalone file
            m.save(map_filename)
            print(f"Map saved as {map_filename}")
            
            # Create iframe to embed the map
            html_content.append(f'''
            <div class="map-container">
                <iframe src="{map_filename}" width="100%" height="100%" frameborder="0" style="border: none; border-radius: 10px;"></iframe>
            </div>
            <p style="text-align: center; color: #666; margin-top: 10px;">
                Heatmap showing {len(valid_heat_data)} points of interest across Czech Republic
                <br><small>Interactive map - pan and zoom to explore</small>
            </p>
            ''')
        else:
            html_content.append('<p>No valid coordinate data available for heatmap.</p>')
    else:
        html_content.append('<p>No data available for heatmap generation.</p>')
    
    html_content.append('</div>')

    # Add charts section
    print("Creating charts and additional visualizations...")
    
    html_content.append('<div class="visualization">')
    html_content.append('<h2 class="section-title">📊 Top Amenities & Shop Types</h2>')
    html_content.append('<div class="chart-grid">')
    
    # Amenities chart
    if amenities:
        html_content.append('<div class="chart-container">')
        html_content.append('<h3>Top 10 Amenities</h3>')
        
        amenity_names = [amenity[0] if amenity[0] is not None else 'Unknown' for amenity in amenities]
        amenity_counts = [amenity[1] for amenity in amenities]
        
        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.barh(amenity_names, amenity_counts, color='skyblue')
        ax.set_xlabel('Count')
        ax.set_title('Most Common Amenities')
        plt.tight_layout()
        
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        amenity_chart = base64.b64encode(buf.getvalue()).decode('utf-8')
        plt.close()
        
        html_content.append(f'<img src="data:image/png;base64,{amenity_chart}" style="max-width: 100%; border-radius: 8px;">')
        html_content.append('</div>')
    
    # Shops chart
    if shops:
        html_content.append('<div class="chart-container">')
        html_content.append('<h3>Top 10 Shop Types</h3>')
        
        shop_names = [shop[0] if shop[0] is not None else 'Unknown' for shop in shops]
        shop_counts = [shop[1] for shop in shops]
        
        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.barh(shop_names, shop_counts, color='lightcoral')
        ax.set_xlabel('Count')
        ax.set_title('Most Common Shop Types')
        plt.tight_layout()
        
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        shop_chart = base64.b64encode(buf.getvalue()).decode('utf-8')
        plt.close()
        
        html_content.append(f'<img src="data:image/png;base64,{shop_chart}" style="max-width: 100%; border-radius: 8px;">')
        html_content.append('</div>')
    
    html_content.append('</div>')
    html_content.append('</div>')

    # Add additional statistics
    print("Fetching additional statistics...")
    html_content.append('<div class="visualization">')
    html_content.append('<h2 class="section-title">🏛️ Additional Statistics</h2>')
    
    # Get tourism statistics
    tourism = run_query(engine, """
        SELECT tourism, COUNT(*) as count 
        FROM planet_osm_point 
        WHERE tourism IS NOT NULL 
        GROUP BY tourism 
        ORDER BY count DESC 
        LIMIT 10
    """, [], 'fetchall')
    
    html_content.append('<div class="chart-grid">')
    
    # Tourism chart
    if tourism:
        html_content.append('<div class="chart-container">')
        html_content.append('<h3>Tourism Features</h3>')
        
        tourism_names = [t[0] if t[0] is not None else 'Unknown' for t in tourism]
        tourism_counts = [t[1] for t in tourism]
        
        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.barh(tourism_names, tourism_counts, color='lightgreen')
        ax.set_xlabel('Count')
        ax.set_title('Tourism Features')
        plt.tight_layout()
        
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        tourism_chart = base64.b64encode(buf.getvalue()).decode('utf-8')
        plt.close()
        
        html_content.append(f'<img src="data:image/png;base64,{tourism_chart}" style="max-width: 100%; border-radius: 8px;">')
        html_content.append('</div>')
    
    # Get landuse statistics
    landuse = run_query(engine, """
        SELECT landuse, COUNT(*) as count 
        FROM planet_osm_polygon 
        WHERE landuse IS NOT NULL 
        GROUP BY landuse 
        ORDER BY count DESC 
        LIMIT 10
    """, [], 'fetchall')
    
    if landuse:
        html_content.append('<div class="chart-container">')
        html_content.append('<h3>Land Use Types</h3>')
        
        landuse_names = [l[0] if l[0] is not None else 'Unknown' for l in landuse]
        landuse_counts = [l[1] for l in landuse]
        
        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.barh(landuse_names, landuse_counts, color='gold')
        ax.set_xlabel('Count')
        ax.set_title('Land Use Types')
        plt.tight_layout()
        
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        landuse_chart = base64.b64encode(buf.getvalue()).decode('utf-8')
        plt.close()
        
        html_content.append(f'<img src="data:image/png;base64,{landuse_chart}" style="max-width: 100%; border-radius: 8px;">')
        html_content.append('</div>')
    
    html_content.append('</div>')
    html_content.append('</div>')

    # Add insights section
    html_content.append("""
        <div class="insight-box">
            <h3>💡 Data Insights</h3>
            <ul>
                <li><strong>Comprehensive Coverage:</strong> The dataset contains {:,} nodes and {:,} ways, indicating detailed mapping coverage.</li>
                <li><strong>Urban Infrastructure:</strong> {:,} buildings mapped with {:,} road segments.</li>
                <li><strong>Commercial Activity:</strong> {:,} points of interest including restaurants, shops, and services.</li>
                <li><strong>Coordinate System:</strong> Database uses SRID {} (Web Mercator).</li>
                <li><strong>Heatmap Visualization:</strong> Shows concentration of amenities and shops across Czech Republic.</li>
                <li><strong>Data Quality:</strong> Interactive map allows exploration of spatial distribution patterns.</li>
            </ul>
        </div>
    """.format(total_nodes, total_ways, buildings, roads_count, pois, srid_info))
    

    html_content.append('<div class="visualization">')
    html_content.append('<h2 class="section-title">❓ How to get data</h2>')
    html_content.append("""<p style="color: #555; font-size: 1.05em; line-height: 1.6; margin-bottom: 25px;">
        This section briefly explains how the dataset used in this dashboard was obtained and prepared. 
        The process is described from a developer's point of view, assuming basic familiarity with 
        programming and databases.
    </p>""")
    list = [
        ("""📥 Data Download""", """The raw OpenStreetMap data was downloaded from <strong>Geofabrik</strong>, a free and open provider of OSM extracts. No registration is required, and the data is fully open-source—meaning anyone can use it, modify it, or build commercial projects with it."""),
        ("""🗄️ Database Setup""", """A fresh <strong>PostgreSQL</strong> database was created. While other SQL systems exist, PostgreSQL is especially suited for geographic data thanks to <strong>PostGIS</strong>, an extension that adds spatial types and functions. After enabling PostGIS, this database becomes the central place where all map data is stored and queried."""),
        ("""📊 Data Import""", """The downloaded OSM file was imported into the database using <strong>osm2pgsql</strong>, a tool that converts the original .osm.pbf format into the schema that PostGIS understands. <br><br><strong>Example command used in this project:</strong><br><code style="background: #f4f4f4; padding: 10px; border-radius: 5px; display: block; margin-top: 10px; font-family: 'Courier New', monospace; overflow-x: auto;">osm2pgsql -d osmcz --create --slim --hstore --cache 2000 czech-republic-251123.osm.pbf -U postgres</code>"""),
        ("""🔍 Data Analysis""", """Once the data was loaded, SQL queries could be run directly against the database to extract statistics about the Czech Republic dataset—everything from counts of amenities to spatial density patterns."""),
        ("""🎨 Dashboard Generation""", """A small Python script then automated the entire process: connecting to the database, executing queries, transforming the results, and generating this interactive dashboard to make the data more readable and visually appealing."""),
    ]
    html_content.append('<div style="display: grid; gap: 20px;">')
    for step_title, entry in list:
        html_content.append(f'''<div style="background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); padding: 20px; border-radius: 10px; border-left: 5px solid #667eea; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
            <h4 style="color: #667eea; margin: 0 0 10px 0; font-size: 1.1em;">{step_title}</h4>
            <p style="color: #555; line-height: 1.7; margin: 0;">{entry}</p>
        </div>''')
    html_content.append('</div>')

    html_content.append('''<div style="margin-top: 25px; padding: 20px; background: #e8eaf6; border-radius: 10px; text-align: center; border: 2px dashed #667eea;">
        <p style="color: #667eea; margin: 0; font-size: 1.05em;">
            <strong>For more user-interactive exploration:</strong><br>
            <a href="https://openstreetmap.cz" target="_blank" style="color: #667eea; text-decoration: none; font-weight: bold; border-bottom: 2px solid #667eea;">openstreetmap.cz</a>
        </p>
    </div>''')
    html_content.append('</div>')

    # Footer
    html_content.append("""
        <div style="text-align: center; margin-top: 40px; color: white;">
            <p>Generated from OSM Czech Republic Database | Data Source: Geofabrik</p>
            <p>Last updated: """ + pd.Timestamp.now().strftime('%Y-%m-%d %H:%M') + """</p>
        </div>
    """)

    html_content.append("""
        </div>
    </body>
    </html>
    """)
    
    # Write to file
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write('\n'.join(html_content))
    
    print("✅ Dashboard successfully generated: index.html")
    print("✅ Heatmap generated: osm_heatmap.html")
    print(f"📊 Database SRID: {srid_info}")
    print(f"📈 Total features: {total_nodes:,} nodes, {total_ways:,} ways, {total_relations:,} relations")
    print(f"🏢 POIs: {pois:,}, Buildings: {buildings:,}, Roads: {roads_count:,}")

if __name__ == "__main__":
    create_osm_dashboard()