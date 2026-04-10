# import modules
import os
import folium
import osmnx as ox
import tempfile
import webbrowser
import pandas as pd
import geopandas as gpd

# define function for adding amenity markers to a folium map as groups
def add_amenity_markers(row, amenity_groups, icons_dictionary):

    # assign geometry of point, polygon, or line to geom
    geom = row.geometry

    # extract coordinates from geom
    if geom.geom_type == 'Point': # all amenities should already be Points
        coords = [geom.y,geom.x]
    else:
        coords = [geom.centroid.y, geom.centroid.x]

    # store name and amenity
    name = row['name']
    amenity = row['amenity']

    # popup will display both name and amenity information in title case if a name exists otherwise only amenity information
    if pd.notna(name):
        popup_text = f"Name: {name.title()}<br>Amenity Type: {amenity.replace('_', ' ').title()}"
    else:
        popup_text = f"Amenity Type: {amenity.replace('_', ' ').title()}"

    # add amenity with marker based on its grouping
    color, icon = icons_dictionary[row.group]
    folium.Marker(location=coords, popup=folium.Popup(popup_text,max_width=250), icon=folium.Icon(color=color, icon=icon, prefix='fa')).add_to(amenity_groups[row['group']])

# define subfolder
subfolder = 'data/Belfast, Northern Ireland/'

# read data files
amenities = gpd.read_file(os.path.join(subfolder,'amenities.geojson'))
buildings = gpd.read_file(os.path.join(subfolder,'buildings.geojson'))
network = ox.load_graphml(os.path.join(subfolder,'network.graphml'))
nodes, edges = ox.graph_to_gdfs(network)

# define amenity groups
amenity_groups = {
    'Education': ['school','outdoor_education_centre','college','university','kindergarten'],
    'Food & Drink': ['fast_food','restaurant','cafe','pub','bar','ice_cream','food_court','vending_machine','drinking_water',
                     'water_point'],
    'Groceries': ['small_supermarket','medium_supermarket','large_supermarket','hypermarket','marketplace'],
    'Postal': ['post_office','post_box','post_depot'],
    'Banking': ['atm','payment_terminal','bank','moneylender','money_lender','bureau_de_change'],
    'Religion': ['place_of_worship','monastery'],
    'Entertainment': ['community_centre','casino','concert_hall','cinema','theatre','library','tanning_salon',
                      'adult_gaming_centre','trampoline_park','bowling_alley','miniature_golf','sports_centre',
                      'fitness_centre','marina','indoor_play','events_venue','arts_centre','music_venue',
                      'studio','nightclub','dance','social_centre','conference_centre','exhibition_centre','golf_course',
                      'fitness_station','bird_hide','swimming_pool','stadium','gambling','sauna','amusement_arcade',
                      'music_school','escape_game','fishing','hackerspace','hookah_lounge'],
    'Healthcare': ['dentist','pharmacy','doctors','clinic','hospital'],
    'Public Services': ['fire_station','police','townhall','courthouse','ranger_station'],
    'Public Transport': ['taxi','bus_stop','bus_station','train_station','train_and_bus_station','ferry_terminal'],
    'Dedicated Greenspaces': ['pitch','park','playground','garden','track','firepit','grave_yard','nature_reserve','dog_park']
}

# assign group to amenities
amenity_to_group = {amenity:group
                    for group, amenities in amenity_groups.items()
                    for amenity in amenities}

# lists all different types of amenities not currently used / assigned to a group
print('The following amenities are not currently being used: ')
print(amenities.loc[~amenities['amenity'].isin(amenity_to_group), 'amenity'].value_counts())

# map amenities and only keep amenities with an assigned group
amenities['group'] = amenities['amenity'].str.lower().map(amenity_to_group)
amenities_to_plot = amenities[amenities['group'].notna()]

# assign icons to amenities based on their group
icons_dictionary = {
    'Education': ('blue', 'book'),
    'Food & Drink': ('lightgray', 'cutlery'),
    'Groceries': ('gray', 'shopping-cart'),
    'Postal': ('pink', 'envelope'),
    'Banking': ('red', 'credit-card'),
    'Religion': ('orange', 'star'),
    'Entertainment': ('purple', 'film'),
    'Healthcare': ('lightgreen', 'medkit'),
    'Public Services': ('lightblue', 'globe'),
    'Public Transport': ('black', 'bus'),
    'Dedicated Greenspaces': ('green', 'tree')
}

# convert data crs into epsg:4326 for folium
amenities_to_plot = amenities_to_plot.to_crs(epsg=4326)
buildings_to_plot = buildings.to_crs(epsg=4326)
edges_to_plot = edges.to_crs(epsg=4326)

# calculate bounds of the map
minx, miny, maxx, maxy = buildings_to_plot.total_bounds

# create folium map with scale bar which is centred on and zoomed into the desired region
m = folium.Map(location=[(miny + maxy)/2,(minx + maxx)/2], tiles=None, control_scale=True)
m.fit_bounds([[miny,minx],[maxy,maxx]])

# plot buildings onto a folium map
bg = folium.FeatureGroup(name='Buildings', show=True)
folium.GeoJson(buildings_to_plot[['id','geometry']],style_function=lambda feature: {"color": "darkred"}).add_to(bg)
bg.add_to(m)

# plot walking network onto a folium map
wng = folium.FeatureGroup(name='Walking Network', show=True)
folium.GeoJson(edges_to_plot[['osmid','geometry']],style_function=lambda feature: {"color": "black"}).add_to(wng)
wng.add_to(m)

# assign markers as groups to be plotted instead of plotting directly
amenity_groups = {}
for group in amenities_to_plot['group'].unique():
    ag = folium.FeatureGroup(name=f'Amenities: {group}', show=False)
    ag.add_to(m)
    amenity_groups[group] = ag

# plot amenities onto a folium map as groups
amenities_to_plot.apply(add_amenity_markers, axis=1, amenity_groups=amenity_groups, icons_dictionary=icons_dictionary)

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