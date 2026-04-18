# import modules
import os
import folium
import osmnx as ox
import tempfile
import webbrowser
import pandas as pd
import geopandas as gpd
import branca.colormap as cm
from config import amenity_groups
from transform import select_subfolder

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

# define a function for creating the style function for add_walkability_buildings
def make_style_function(colormap, walkability):

    # utilise an inner function to remember colormap and walkability
    def style_function(feature):

        # extract walkability index
        val = feature['properties'].get(walkability)

        # convert value into a colour and return it with the other styling instructions
        return {
            'fillColor': colormap(val),
            'color': 'black',
            'fillOpacity': 1,
            'weight': 1,
        }

    # return the inner function
    return style_function

# define function for adding buildings to folium map with scoring for a given distance, and colouring buildings based on overall score
def add_walkability_buildings(buildings, scores, t=15):
    # define the name of the walkability index based on selected walking time
    walkability = f'{t} Overall'

    # set the fields and aliases to be added to the building tool tip in the map
    hover_fields = [f'{t} {s}' for s in scores]
    hover_aliases = [f'{s} ({t} min)' for s in scores]

    # define the tooltip using the fields and aliases previously defined
    tooltip = folium.GeoJsonTooltip(fields = hover_fields, aliases = hover_aliases, sticky = True)

    # define the colourmap to match the expected scale of the walkability score and set caption
    colormap = cm.linear.viridis.scale(0,100)
    colormap.caption = f'{t}-minute Walkability Score'

    # plot the buildings with their associated data onto the folium map
    folium.GeoJson(
        buildings,
        name = f'Buildings with {t}-minute Walkability Score',
        style_function = make_style_function(colormap, walkability),
        tooltip = tooltip
    ).add_to(m)

    # add the colourmap to the folium map
    colormap.add_to(m)

    return m

# define subfolder
subfolder = select_subfolder()

# read data files
amenities = gpd.read_file(os.path.join(subfolder,'amenities.geojson'))
buildings = gpd.read_file(os.path.join(subfolder,'buildings_scored.geojson'))
network = ox.load_graphml(os.path.join(subfolder,'network.graphml'))
nodes, edges = ox.graph_to_gdfs(network)

# define selection of walkability time (can be 15, 30, or 60)
selection = 15

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

# define a list of the names of the scoring indexes to use in building tooltips
scores = ['Overall'] + list(amenity_groups.keys())

# plot buildings onto a folium map
add_walkability_buildings(buildings_to_plot, scores, 15)

# plot walking network onto a folium map
wng = folium.FeatureGroup(name='Walking Network', show=False)
folium.GeoJson(edges_to_plot[['osmid','geometry']],style_function=lambda feature: {"color": "black"}).add_to(wng)
wng.add_to(m)

# assign markers as groups to be plotted instead of plotting directly
amenity_groupings = {}
for group in amenities_to_plot['group'].unique():
    ag = folium.FeatureGroup(name=f'Amenities: {group}', show=False)
    ag.add_to(m)
    amenity_groupings[group] = ag

# plot amenities onto a folium map as groups
amenities_to_plot.apply(add_amenity_markers, axis=1, amenity_groups=amenity_groupings, icons_dictionary=icons_dictionary)

# add base maps to folium map
folium.TileLayer(tiles='Esri WorldImagery', name='Satellite (Esri)').add_to(m)
folium.TileLayer(tiles='CartoDB positron', name='Light Map (CartoDB)').add_to(m)
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