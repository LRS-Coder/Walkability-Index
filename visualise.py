# import modules
import os
import folium
import osmnx as ox
import tempfile
import webbrowser
import pandas as pd
import geopandas as gpd
import branca.colormap as cm
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
from config import amenity_groups, folium_threshold
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

# define function for adding buildings to folium map with scoring for a given distance, and colouring buildings based on overall score
def add_walkability_buildings(buildings, scores, m, t=15):
    # define the name of the walkability index based on selected walking time
    walkability = f'{t} Overall'

    # set the fields and aliases to be added to the building tool tip in the map
    hover_fields = [f'{t} {s}' for s in scores]
    hover_aliases = [f'{s} ({t} min)' for s in scores]

    # define the tooltip using the fields and aliases previously defined
    tooltip = folium.GeoJsonTooltip(fields = hover_fields, aliases = hover_aliases, sticky = True)

    # define the colourmap to match the expected scale of the walkability score and apply colourmap
    colourmap = cm.linear.viridis.scale(0,100)
    buildings['colour'] = buildings[f'{selection} Overall'].apply(colourmap)

    # set caption
    colourmap.caption = f'{t}-minute Walkability Score'

    # plot the buildings with their associated data onto the folium map
    folium.GeoJson(
        buildings,
        name = f'Buildings with {t}-minute Walkability Score',
        style_function = lambda f: {
            'fillColor': f['properties']['colour'],
            'color': 'black',
            'fillOpacity': 1,
            'weight': 1,
        },
        tooltip = tooltip
    ).add_to(m)

    # add the colourmap to the folium map
    colourmap.add_to(m)

    return m

# define function to create an interactive folium map
def create_interactive_map(buildings, amenities, edges, selection, icons_dictionary):

    # prints to let user know an interactive map is being created
    print('Creating an interactive map...')

    # convert data crs into epsg:4326 for folium
    amenities_to_plot = amenities.to_crs(epsg=4326)
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
    add_walkability_buildings(buildings_to_plot, scores, m, selection)

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
    try:
        webbrowser.open(f'file://{temp_path}')
        while True:
            satisfactory = input('Is this map satisfactory? (yes/no): ').strip().lower()

            # exit while condition
            if satisfactory in ['y', 'yes']:
                print('User is satisfied with the map.')
                break

            # ask user if they would like to try running the static map function
            elif satisfactory in ['n', 'no']:
                try_static = input("Please type 'yes' if you would like to produce a static map: ").strip().lower()

                # create a static map if user entered yes
                if try_static in ['y', 'yes']:
                    create_static_map(buildings, edges, selection)

                # print that user does not want to create a static map if not yes
                else:
                    print('User does not want to create a static map.')

                # exit while condition
                break

            # ask question again
            else:
                print("Invalid Input. Please type 'yes'.")
                continue

    # delete the temporary file
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

# define function to create a static matplotlib map
def create_static_map(buildings, edges, selection):

    # prints to let user know a static map is being created
    print('Creating a static map...')

    # update buildings and edges to Irish Transverse Mercator (EPSG:2157)
    buildings = buildings.to_crs(2157)
    edges = edges.to_crs(2157)

    # estimate map size and use to determine linewidth (ensure between 0.05 and 2) and to create a height relative to a fixed width of 20
    xmin, ymin, xmax, ymax = buildings.total_bounds
    lw =  max(0.05, min(2000 / max(xmax - xmin, ymax - ymin), 2))
    height = (20 * (ymax - ymin)/(xmax - xmin))

    # create the figure and axis objects to add the map to with axis relating to extent
    fig, ax = plt.subplots(figsize=(20,height))

    # ensure geography is preserved and buildings and edges are not stretched
    ax.set_aspect('equal')

    # ensure colour bar that stays in line with the map
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="5%", pad=0.1, axes_class=plt.Axes)

    # add walking network to the map
    edges.plot(
        linewidth = lw,
        color = 'black',
        ax = ax
    )

    # add buildings to the map
    buildings.plot(
        column = f'{selection} Overall',
        cmap = 'viridis',
        vmin=0,
        vmax=100,
        linewidth = 0,
        ax = ax,
        legend = True,
        cax = cax,
        legend_kwds = {'label': f'{selection}-minute walkability score'}
    )

    # label axes
    ax.set_xlabel('ITM Easting (m)')
    ax.set_ylabel('ITM Northing (m)')

    # save and display map
    plt.savefig(f'{subfolder}{selection}_map.png', dpi=600, bbox_inches='tight')
    plt.show()

# define subfolder
subfolder = select_subfolder()

# read data files
amenities = gpd.read_file(os.path.join(subfolder,'amenities.geojson'))
buildings = gpd.read_file(os.path.join(subfolder,'buildings_scored.geojson'))
network = ox.load_graphml(os.path.join(subfolder,'network.graphml'))
nodes, edges = ox.graph_to_gdfs(network)

# count the number of buildings in the file
building_count = len(buildings)

# define selection of walkability time (can be 15, 30, or 60)
while True:
    try:

        # user can select a value of 15, 30, or 60 only
        selection = int(input('Select a timeframe for the Walkability Index (15, 30, or 60 minutes): '))
        if selection in [15, 30, 60]:
            break

        # if user enters any other number they will be prompted to try again
        else:
            print('Please type 15, 30, or 60.')
            continue

    # if user inputs something other than a number they will be prompted to try again
    except Exception:
        print('User did not enter a number, please try again')

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

# ask if user wants an interactive map if the building count is less than
if building_count > folium_threshold:
    print('Dataset too large for an interactive map.')
    create_static_map(buildings, edges, selection)

else:
    while True:
        folium_choice = input('Would you like to create an interactive map? (yes/no): ').strip().lower()

        # act on decision
        if folium_choice in ['y', 'yes']:
            print('User wants an interactive map.')
            create_interactive_map(buildings, amenities_to_plot, edges, selection, icons_dictionary)
            break
        elif folium_choice in ['n', 'no']:
            print('User DOES NOT want an interactive map.')
            create_static_map(buildings, edges, selection)
            break
        else:
            print("Invalid Input. Please type 'yes' or 'no'.")
            continue