# import modules
import os
import folium
import osmnx as ox
import tempfile
import webbrowser
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, box
import pyproj

# define function for creating a circular polygon around a point using local UTM projection
def create_circle_polygon(lat, lon, radius_km):

    # determine local UTM CRS
    utm_crs = pyproj.CRS.from_proj4(f"+proj=utm +zone={int((lon+180)/6)+1} +datum=WGS84 +units=m +no_defs ")

    # create a point, convert to local UTM and buffer by radius, convert back to epsg:4326
    point = gpd.GeoSeries([Point(lon, lat)], crs="epsg:4326")
    circle_polygon = point.to_crs(utm_crs).buffer(radius_km*1000).to_crs("epsg:4326")[0]
    return circle_polygon

# define function for assigning amenity to supermarkets based on size
def assign_supermarket_amenity(size_band):
    if '< 3,013 ft2' in size_band:
        return 'small_supermarket'
    elif '3,013 < 15,069 ft2' in size_band:
        return 'medium_supermarket'
    elif '15,069 < 30,138 ft2' in size_band:
        return 'large_supermarket'
    else:
        return 'hypermarket'

# define function for ensuring location is giving the correct boundary
def osm_download_confirm():

    # user inputs locations until satisfied with the boundary they would be downloading
    while True:

        method = input("Method 1: OpenStreetMap boundary \nMethod 2: Circular boundary from OpenStreetMap point"
                       "\nMethod 3: Manual bounding box \nPlease select a method (1,2,3) or enter 'exit': ").strip().lower()

        # stop running code
        if method in ["e","exit"]:
            print('User chose to exit.')
            return None

        # return to start if 1, 2, or 3 was not entered
        elif method not in ["1","2","3","e","exit"]:
            print("Input must be 1, 2, 3, or exit. Please try again.")
            continue

        # user inputs a location
        location = input("Enter a location (e.g. Paris, France): ")

        # OpenStreetMap boundary
        if method == "1":

            try:
                # download boundary and convert to a singular polygon
                boundary = ox.geocode_to_gdf(location)
                download_boundary = boundary.geometry.union_all()

            # return to start if the boundary could not be found
            except Exception:
                print("Could not locate the boundary. Please try again.")
                continue

            # plot boundary on map
            m = boundary.explore(color='black',tiles=None,name=location)

        # circular boundary from OpenStreetMap point
        elif method == "2":

            try:
                # download coordinates of the location
                lat, lon = ox.geocode(location)

            # return to start if the boundary could not be found
            except Exception:
                print("Could not locate the place. Please try again.")
                continue

            try:
                # user inputs a radius
                radius_km = float(input("Enter a radius (km): "))
                download_boundary = create_circle_polygon(lat,lon,radius_km)

            # return to start if there is a problem with the radius
            except Exception:
                print("Invalid radius. Please try again.")
                continue

            # plot circular boundary on map
            m = folium.Map(location=[lat,lon], tiles=None)
            folium.GeoJson(download_boundary,style_function=lambda feature: {"color": "black"}).add_to(m)

        # manual bounding box
        elif method == "3":

            # user inputs coordinates
            coords = input("Enter the coordinates in decimal degrees as lat min, lon min, lat max, lon max (e.g. 48.73,2.13,49.02,2.58): ")

            try:
                # convert users input into floating point coordinates
                lat_min, lon_min, lat_max, lon_max = map(float, coords.split(','))
                download_boundary = box(lon_min, lat_min, lon_max, lat_max)

            # return to start if there is a problem with the coordinates
            except Exception:
                print("Invalid coordinates. Please try again.")
                continue

            m = folium.Map(location=[(lat_min + lat_max)/2, (lon_min + lon_max)/2], tiles=None)
            folium.GeoJson(download_boundary,style_function=lambda feature: {"color": "black"}).add_to(m)

        # add base maps to folium map
        folium.TileLayer(tiles='CartoDB positron', name='Light Map (CartoDB').add_to(m)
        folium.TileLayer(tiles='Esri WorldImagery',name='Satellite (Esri)').add_to(m)
        folium.LayerControl().add_to(m)

        # create a temporary file to for folium image
        with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as tf:
            temp_path = tf.name
        m.save(temp_path)

        # display boundary plot in browser and ask whether boundary is satisfactory
        webbrowser.open(f'file://{temp_path}')
        while True:
            satisfactory = input('Is this area satisfactory? (yes/no): ').strip().lower()

            # act on decision
            if satisfactory in ['y','yes']:
                print('User is satisfied with the boundary.')
                osm_download_all(location, download_boundary)
                print('Successfully downloaded all files')
                break
            elif satisfactory in ['n','no']:
                print('User is NOT satisfied with the boundary.')
                break
            else:
                print("Invalid Input. Please type 'yes' or 'no'.")
                continue

        # delete the temporary file
        os.remove(temp_path)

# define function for downloading from all required data from OpenStreetMap
def osm_download_all(location, boundary, folder="data"):

    # formats the location name for use a filename
    location_filename = location.replace(",", "").replace(" ", "_")

    # download buildings, amenities (including leisure), and walking network
    buildings = ox.features_from_polygon(boundary, tags = {"building": True})
    amenities = ox.features_from_polygon(boundary, tags = {"amenity": True, "leisure": True})
    network = ox.graph.graph_from_polygon(boundary, network_type = "walk")

    # drop unnecessary columns including filling empty amenity column with leisure column (requires flattening)
    buildings = buildings.reset_index()[['id','building','geometry']]
    amenities = amenities.reset_index()
    amenities['amenity'] = amenities['amenity'].fillna(amenities['leisure'])
    amenities = amenities[['id','name','amenity','geometry']]

    # define target crs from network to accurately calculate the centre of amenities
    network_proj = ox.project_graph(network)
    target_crs = network_proj.graph['crs']

    # convert crs of amenities to match network
    amenities = amenities.to_crs(target_crs)

    # convert all amenities to nodes
    amenities['geometry'] = amenities.geometry.centroid

    # convert crs of amenities back to epsg_4326
    amenities = amenities.to_crs(epsg=4326)

    # load bank and supermarket data
    banks = pd.read_csv("data/geolytix_uk_open_bank_branches.csv")
    supermarkets = pd.read_csv("data/geolytix_retailpoints_v40_202601.csv")

    # create geodataframes for bank and supermarket data and set the geometry using points_from_xy
    banks_gdf = gpd.GeoDataFrame(banks,
                                geometry=gpd.points_from_xy(banks['long_wgs84'], banks['lat_wgs84']),
                                crs='epsg:4326')
    supermarkets_gdf = gpd.GeoDataFrame(supermarkets,
                                geometry=gpd.points_from_xy(supermarkets['long_wgs'], supermarkets['lat_wgs']),
                                crs='epsg:4326')

    # only keep bank and supermarket data within the desired boundry
    banks_gdf = banks_gdf[banks_gdf.geometry.within(boundary)]
    supermarkets_gdf = supermarkets_gdf[supermarkets_gdf.geometry.within(boundary)]

    # complete bank and supermarket columns to match OpenStreetMap data
    banks_gdf = banks_gdf.rename(columns ={'branch_name':'name'})
    banks_gdf['amenity'] = 'bank'
    supermarkets_gdf = supermarkets_gdf.rename(columns ={'store_name':'name'})
    supermarkets_gdf['amenity'] = supermarkets_gdf['size_band'].apply(assign_supermarket_amenity)

    # combine amenities data with banks and supermarkets data
    amenities = pd.concat([amenities[['id','name','amenity','geometry']],
                           banks_gdf[['id','name','amenity','geometry']],
                           supermarkets_gdf[['id','name','amenity','geometry']]],
                          ignore_index=True)

    # save buildings
    buildings_file = os.path.join(folder, f"{location_filename}_buildings.geojson")
    buildings.to_file(buildings_file, driver = "GeoJSON")
    # save amenities
    amenities_file = os.path.join(folder, f"{location_filename}_amenities.geojson")
    amenities.to_file(amenities_file, driver = "GeoJSON")
    # save walking network
    network_file = os.path.join(folder, f"{location_filename}_network.graphml")
    ox.save_graphml(network, network_file)

osm_download_confirm()