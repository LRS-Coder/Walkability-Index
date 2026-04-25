# import modules from standard library
import os
import tempfile
import webbrowser

# import modules from third-party
import folium
import osmnx as ox
import pandas as pd
import geopandas as gpd
import branca.colormap as cm
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from mpl_toolkits.axes_grid1 import make_axes_locatable

# import local modules
from config import amenity_groups, folium_threshold

# define function for adding amenity markers to a folium map as groups
def add_amenity_markers(row, amenity_groups, icons_dictionary):
    """
    Add amenity markers with their colour and icon based on the amenity's group.

    Extracts coordinates from the geometry of the amenity.
    Add the name and type of amenity to its popup.
    Assign colour and icon of the popup based on the amenity's group.

    Parameters
    ----------

    row : pandas.Series
        row from a GeoDataFrame containing information related to its geometry, name, and type.

    amenity_groups : dict
        dictionary mapping an amenity grouping with the amenities in the group.

    icons_dictionary : dict
        dictionary mapping an amenity grouping with the colour and icon that represents the grouping.

    Returns
    -------

    None
    """

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
    """
    Add buildings with an assigned colour based on their Walkability score for a given walking time.

    Adds tooltips to the buildings providing their score breakdown.
    Assign a colour from viridis to each building based on their Walkability score for a given walking time.
    Add the colour bar to the folium map.

    Parameters
    ----------

    buildings : geopandas.GeoDataFrame
        GeoDataFrame containing geometries and scores for each building.

    scores : list
        list of the grouping names and 'Overall' to construct tooltips.

    m : folium.Map
        folium map the buildings are to be added to.

    t : int, default 15
        walking time threshold in minutes.

    Returns
    -------

    m : folium.Map
        updated folium map with the buildings and colour bar added.
    """

    # define the name of the walkability index based on selected walking time
    walkability = f'{t} Overall'

    # set the fields and aliases to be added to the building tool tip in the map
    hover_fields = [f'{t} {s}' for s in scores]
    hover_aliases = [f'{s} ({t} min)' for s in scores]

    # define the tooltip using the fields and aliases previously defined
    tooltip = folium.GeoJsonTooltip(fields = hover_fields, aliases = hover_aliases, sticky = True)

    # define the colourmap to match the expected scale of the walkability score and apply colourmap
    colourmap = cm.linear.viridis.scale(0,100)
    buildings['colour'] = buildings[f'{t} Overall'].apply(colourmap)

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

# define function to create a box style scale bar for static maps
def add_scalebar(ax, n=4, location=(0.6,0.03)):
    """
    Add a box style scale bar to a matplotlib axis.

    Creates a segmented scale bar with alternating colours (black and white) and distance labels.
    The scale bar is formated such that it can be in meters or kilometers.
    The scale bar is adjusted so it represents are "nice" (e.g. 500, 1000, 2000, 5000) overall length.
    The scale bar appears near the bottom-right of the map with the default location with a padded layer beneath.

    Parameters
    ----------

    ax : matplotlib.axes.Axes
        matplotlib axis where scale bar will be added.

    n : int, default 4
        number of segments the scale bar consists of.

    location : tuple of float, default (0.6,0.03)
        position of the scale bar relative to the map where (1,1) is the top-right corner.

    Returns
    -------

    None
    """

    # define axis limits in projected coordinates
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()

    # calculate the extent of the map
    xmin, xmax = xlim
    ymin, ymax = ylim
    map_width = xmax - xmin
    map_height = ymax - ymin

    # define starting coordinates based on desired location on map
    x0 = xmin + location[0] * map_width
    y0 = ymin + location[1] * map_height

    # select a nice length value from list
    nice_values = [
        10, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000, 50000
    ]
    length = min(nice_values, key=lambda x: abs(x - (map_width * 0.25)))

    # select units based on length
    if length >= 1000:
        unit = 'km'
        scale = 1000
    else:
        unit = 'm'
        scale = 1

    # define segment size and height
    seg = length / n
    h = map_height * 0.02

    # define padding extent beyond scale bar
    pad_x_left = seg * 0.25
    pad_x_right = seg * 1.5
    pad_y_top = h * 0.25
    pad_y_bottom = h * 2

    # add padding around scale bar to aid readability
    ax.add_patch(Rectangle(
        (x0 - pad_x_left, y0 - pad_y_bottom),
        length + pad_x_left + pad_x_right,
        h + pad_y_top + pad_y_bottom,
        facecolor='white',
        edgecolor='none',
        alpha=0.8
    ))

    # add alternating boxes (black and white)
    for i in range(n):

        # alternate between black and white boxes
        colour = 'black' if i % 2 == 0 else 'white'

        # create the rectangle for each segment
        ax.add_patch(Rectangle(
            (x0 + i * seg, y0),
            seg,
            h,
            facecolor=colour,
            edgecolor='black',
            linewidth=1
        ))

    # add tick labels to the scale bar
    for i in range(n+1):

        # update x position
        x_pos = x0 + i * seg

        # update tick value
        value = (i*seg) / scale

        # add unit to last tick
        if i == n:
            label = f'{value:g} {unit}'
            ha = 'left'
        else:
            label = f'{value:g}'
            ha = 'center'

        # add the label to the scale bar
        ax.text(
            x_pos,
            y0 - (h/2),
            label,
            ha=ha,
            va='top',
            fontsize=9
        )

# define function to create an interactive folium map
def create_interactive_map(subfolder, buildings, amenities, edges, selection, icons_dictionary):
    """
    Create and display an interactive folium map.

    Generates a folium map containing buildings coloured based on their walkability.
    The folium map enables amenities to be toggled on and off by their category.
    The walking network for the location can be toggled on and off.
    User caan generate a static map from within this function if not satisfied with the interactive map.

    Parameters
    ----------

    subfolder : str
        matplotlib axis where scale bar will be added.

    buildings : geopandas.GeoDataFrame
        GeoDataFrame containing geometries and scores for each building.

    amenities : geopandas.GeoDataFrame
        GeoDataFrame containing location of amenities and their classes.

    edges : geopandas.GeoDataFrame
        GeoDataFrame representing the edges of the walking network.

    selection : int
        selected walkability threshold of 15, 30, or 60 minutes.

    icons_dictionary : dict
        dictionary mapping an amenity grouping with the colour and icon that represents the grouping.

    Returns
    -------

    None
    """

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
                    create_static_map(subfolder, buildings, edges, selection)

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
def create_static_map(subfolder, buildings, edges, selection):
    """
    Create and display a static matplotlib map.

    Generates a matplotlib map containing buildings coloured based on their walkability.
    The matplotlib map contains a scale bar, the colour bar, and labels the axis based on Irish Transverse Mercator (ITM).
    Saves the map as a .png image.

    Parameters
    ----------

    subfolder : str
        matplotlib axis where scale bar will be added.

    buildings : geopandas.GeoDataFrame
        GeoDataFrame containing geometries and scores for each building.

    edges : geopandas.GeoDataFrame
        GeoDataFrame representing the edges of the walking network.

    selection : int
        selected walkability threshold of 15, 30, or 60 minutes.

    Returns
    -------

    None
    """

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

    # add scale bar to the map
    add_scalebar(ax)

    # label axes
    ax.set_xlabel('ITM Easting (m)')
    ax.set_ylabel('ITM Northing (m)')

    # save and display map
    plt.savefig(f'{subfolder}{selection}_map.png', dpi=600, bbox_inches='tight')
    plt.show()

# define function to select the desired walkability time (can be 15, 30, or 60)
def get_timeframe():
    """
    Confirm a walkability time ensuring it is either 15, 30, or 60 minutes.

    Returns
    -------

    selection : int
        selected walkability threshold of 15, 30, or 60 minutes.
    """

    while True:
        try:

            # user can select a value of 15, 30, or 60 only
            selection = int(input('Select a timeframe for the Walkability Index (15, 30, or 60 minutes): '))
            if selection in [15, 30, 60]:
                return selection

            # if user enters any other number they will be prompted to try again
            else:
                print('Please type 15, 30, or 60.')
                continue

        # if user inputs something other than a number they will be prompted to try again
        except Exception:
            print('User did not enter a number, please try again')

# define function for running the visualise pipeline
def run_visualise(subfolder):
    """
    Run visualise to create a static and / or interactive map.

    Define input file paths based on the subfolder.
    Have the user select a timeframe to map.
    Allow user to select an interactive map if number of buildings is not too large to display, always allow the creation of a static map.

    Parameters
    ----------

    subfolder : str
        path to the subfolder where all data for the location of interest is stored.

    Returns
    -------

    None
    """


    # read data files
    amenities = gpd.read_file(os.path.join(subfolder, 'amenities.geojson'))
    buildings = gpd.read_file(os.path.join(subfolder, 'buildings_scored.geojson'))
    network = ox.load_graphml(os.path.join(subfolder, 'network.graphml'))
    edges = ox.graph_to_gdfs(network)[1]

    # count the number of buildings in the file
    building_count = len(buildings)

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

    # have the user select a timeframe
    selection = get_timeframe()

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
                create_interactive_map(subfolder, buildings, amenities_to_plot, edges, selection, icons_dictionary)
                break
            elif folium_choice in ['n', 'no']:
                print('User DOES NOT want an interactive map.')
                create_static_map(subfolder, buildings, edges, selection)
                break
            else:
                print("Invalid Input. Please type 'yes' or 'no'.")
                continue