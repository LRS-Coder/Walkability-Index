# import modules
import os
import folium
import osmnx as ox
import tempfile
import webbrowser
import geopandas as gpd

# define function for adding amenity markers to a folium map
def add_amenity_markers(row, map_name, icons_dictionary):

    # assign geometry of point, polygon, or line to geom
    geom = row.geometry

    # extract coordinates from geom
    if geom.geom_type == 'Point':
        coords = [geom.y,geom.x]
    else:
        coords = [geom.centroid.y, geom.centroid.x]

    # add amenity with marker based on its grouping
    color, icon = icons_dictionary[row.group]
    folium.Marker(location=coords, popup=row.amenity, icon=folium.Icon(color=color, icon=icon)).add_to(map_name)

# read data files
amenities = gpd.read_file('data/Bushmills_Northern_Ireland_amenities.geojson')
buildings = gpd.read_file('data/Bushmills_Northern_Ireland_buildings.geojson')
network = ox.load_graphml('data/Bushmills_Northern_Ireland_network.graphml')
nodes, edges = ox.graph_to_gdfs(network)

# lists all different types of amenities
print(amenities['amenity'].value_counts())

# define amenity groups
amenity_groups = {
    'education': ['school','outdoor_education_centre'],
    'food_drink': ['fast_food','restaurant','cafe','pub','bar'],
    'postal': ['post_office','post_box'],
    'banking': ['atm'],
    'religion': ['place_of_worship'],
    'entertainment': ['community_centre']
}

# assign group to amenities
amenity_to_group = {amenity:group
                    for group, amenities in amenity_groups.items()
                    for amenity in amenities}

# map amenities and only keep amenities with an assigned group
amenities['group'] = amenities['amenity'] = amenities['amenity'].str.lower().map(amenity_to_group)
amenities_to_plot = amenities[amenities['group'].notna()]

# assign icons to amenities based on their group
icons_dictionary = {
    'education': ('blue', 'book'),
    'food_drink': ('lightgray', 'cutlery'),
    'postal': ('pink', 'envelope'),
    'banking': ('red', 'credit-card'),
    'religion': ('orange', 'star'),
    'entertainment': ('purple', 'film')
}

# convert data crs into epsg:4326 for folium
amenities_to_plot = amenities_to_plot.to_crs(epsg=4326)
buildings_to_plot = buildings.to_crs(epsg=4326)
edges_to_plot = edges.to_crs(epsg=4326)

# plot buildings, walking network, and amenities onto a folium map
m = folium.Map(location=[buildings.geometry.centroid.to_crs(epsg=4326).y.mean(),buildings.geometry.centroid.to_crs(epsg=4326).x.mean()], tiles=None)
folium.GeoJson(buildings_to_plot[['id','geometry']],style_function=lambda feature: {"color": "darkred"}).add_to(m)
folium.GeoJson(edges_to_plot[['osmid','geometry']],style_function=lambda feature: {"color": "black"}).add_to(m)
amenities_to_plot.apply(add_amenity_markers, axis=1, map_name=m, icons_dictionary=icons_dictionary)

# add base maps to folium map
folium.TileLayer(tiles='CartoDB positron', name='Light Map (CartoDB').add_to(m)
folium.TileLayer(tiles='Esri WorldImagery', name='Satellite (Esri)').add_to(m)
folium.LayerControl().add_to(m)

# create a temporary file to for folium image
with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as tf:
    temp_path = tf.name
m.save(temp_path)

# display boundary plot in browser and ask whether boundary is satisfactory
webbrowser.open(f'file://{temp_path}')

while True:
    satisfactory = input('Is this map satisfactory? (yes): ').strip().lower()

    # act on decision
    if satisfactory in ['y', 'yes']:
        print('User is satisfied with the map.')
        break
    else:
        print("Invalid Input. Please type 'yes'.")
        continue

# delete the temporary file
os.remove(temp_path)