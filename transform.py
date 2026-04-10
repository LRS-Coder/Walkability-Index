# import modules
import os
import osmnx as ox
import networkx as nx
import pandas as pd
import geopandas as gpd
from collections import defaultdict, Counter

# define function to count the total amenities across all reachable nodes
def count_amenities(nodes):
    counts = Counter()

    # look up distances per node
    for n in nodes:
        counts.update(amenity_index.get(n, {}))
    return counts

# define subfolder
subfolder = 'data/Coleraine, Northern Ireland/'

# read data files
amenities = gpd.read_file(os.path.join(subfolder,'amenities.geojson'))
buildings = gpd.read_file(os.path.join(subfolder,'buildings.geojson'))
network = ox.load_graphml(os.path.join(subfolder,'network.graphml'))

# reset the index of amenities
amenities = amenities.reset_index(drop=True)

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

# define the amenities that are valid based on if they are in amenity_groups
valid_amenities = set(a for group in amenity_groups.values() for a in group)

# remove amenities that are not in valid_amenities
amenities = amenities[amenities['amenity'].isin(valid_amenities)].copy()

# define walking speed
walking_speed = 81 # metres per minute (1.35m/s)

# add a travel time attribute to every edge
for u, v, k, data in network.edges(data=True, keys=True):
    data['time'] = data['length'] / walking_speed

# snap buildings and amenities to network nodes, with many buildings using the same node it should run faster
# error introduced will be smaller for shorter roads
building_nodes = ox.nearest_nodes(network, X=buildings.geometry.representative_point().x.tolist(), Y=buildings.geometry.representative_point().y.tolist())
amenity_nodes = ox.nearest_nodes(network, X=amenities.geometry.x.tolist(), Y=amenities.geometry.y.tolist())

# define an amenity index as a dictionary with the purpose of counting
amenity_index = defaultdict(Counter)

# for each amenity add a count to its closest node
for i in range(len(amenities)):
    node = amenity_nodes[i]
    amenity_type = amenities.iloc[i]['amenity']
    amenity_index[node][amenity_type] += 1

# define shared_building_nodes as dictionary containing a list
shared_building_nodes = defaultdict(list)

# buildings which have the same closest node are grouped in the shared_building_nodes dictionary
for b_index, node in enumerate(building_nodes):
    # use ids from the buildings file
    id = int(buildings.iloc[b_index]['id'])
    shared_building_nodes[node].append(id)

# define all_building_results as an empty list
all_building_results = []

# loop through buildings and their nodes
for origin_node, building_id in shared_building_nodes.items():

    # compute travel times from one node to all other nodes within a 60 minute walking distance using dijkstra
    travel_time = nx.single_source_dijkstra_path_length(network, origin_node, cutoff=60, weight='time')

    # create unordered sets for 15 minutes, 30 minutes, and 60 minutes (60 minute includes all reachable nodes)
    nodes_15 = set()
    nodes_30 = set()
    nodes_60 = set(travel_time.keys())

    # assign nodes to 15 minute, and 30 minute sets based on travel time
    for n, t in travel_time.items():
        if t <= 15:
            nodes_15.add(n)
        if t <= 30:
            nodes_30.add(n)

    # store amenity counts for each time threshold
    all_building_results.append({"building_id": building_id,
        "15min": count_amenities(nodes_15),
        "30min": count_amenities(nodes_30),
        "60min": count_amenities(nodes_60)})

# create a pandas data frame with the results
df = pd.DataFrame(all_building_results)

# save results to a csv file
df.to_csv(os.path.join(subfolder, 'buildings_access.csv'), index=False)