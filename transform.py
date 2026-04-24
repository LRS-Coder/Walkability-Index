# import modules from standard library
import os
import ast
from collections import defaultdict, Counter

# import modules from third-party
import osmnx as ox
import networkx as nx
import pandas as pd
import geopandas as gpd

# import local modules
import config
from scoring import scorer_methods

# calculate the sum of all weights
weights = config.scorer_weights
total_weights = sum(weights.values())

# define walking speed and valid amenities from config
walking_speed = config.walking_speed
valid_amenities = config.valid_amenities

# define function to convert Counter() string into a dictionary
def counter_parser(s):
    """
    Parse a Counter object into a dictionary.

    Convert string representation of collections.Counter object (e.g. "Counter({'bus_stop': 6, 'restaurant': 2, 'fast_food': 2, 'place_of_worship': 2})") to a dictionary.

    Parameters
    ----------

    s : str, dict, or NaN
        stored Counter value, read from csv.

    Returns
    -------

    dict
        dictionary mapping amenities to their counts for a given walking distance to a node.
        returns nothing if parameter s was empty or parsing fails.
    """

    # check if empty return empty if so
    if pd.isna(s):
        return {}

    # check if already formatted as a dictionary (should not be true with current storing), return if it is
    if isinstance(s,dict):
        return s

    # convert to string and remove any whitespaces at its start or end
    s = str(s).strip()

    # check if the Counter string is empty return empty if so
    if s == 'Counter()' or s == 'Counter({})':
        return {}

    # check if the expected format Counter(...) and remove Counter( and ) if so
    if s.startswith('Counter(') and s.endswith(')'):
        inner = s[len('Counter('):-1]

        # try to turn the string into an object (should turn into dictionary)
        try:
            return ast.literal_eval(inner)

        # print an error message if it was not able to turn the string into a dictionary
        except Exception as e:
            print('Counter parse error: ', s)
            print(e)
            return {}

    # try to turn the string into an object (should turn into dictionary)
    try:
        return ast.literal_eval(s)

    # print an error message if it was not able to turn the string into a dictionary
    except Exception as e:
        print('General parse error: ', s)
        print(e)
        return {}

# define function to ensure all ids are lists which can later be exploded
def id_parser(d):
    """
    Ensure building IDs are returned as a list.

    Parameters
    ----------

    d : str, list, int, or NaN
        building ID(s) closest to the node.

    Returns
    -------

    list
        list of building ID(s) closest to the node.
        returns nothing if parameter d was empty.
    """

    # check if id is missing (should not be the case) and return nothing if the case
    if pd.isna(d):
        return []

    # check if already a list and return it if the case
    if isinstance(d,list):
        return d

    # if a string attempts to convert into a list (list is the format it should be parsed into)
    if isinstance(d,str):
        return ast.literal_eval(d)
    return [d]

# define function to count the total amenities across all reachable nodes
def count_amenities(nodes, amenity_index):
    """
    Combine amenity counts from multiple nodes into a single Counter representing total accessible amenities from a node.

    Parameters
    ----------

    nodes : iterable
        collection of node ID(s).

    amenity_index : dict[int, collections.Counter]
        mapping of node IDs to counts of amenities by type of amenity.

    Returns
    -------

    counts : collections.Counter
        combined counts of amenities reachable from a given node.
    """

    # set counts as a Counter object
    counts = Counter()

    # look up distances per node
    for n in nodes:
        counts.update(amenity_index.get(n, {}))
    return counts

# define function for counting amenities within 15min, 30min, and 60min walking distances and write to a file
def building_access(access_path, amenities_path, buildings_path, network_path):
    """
    Compute walking accessibility to amenities for each building.

    Calculates the number of amenities within a 15, 30, and 60 minute walk of the closest node to a building.
    Snaps buildings to their nearest network node introduces some spatial inaccuracies but improves performance.
    Dijkstra's algorithm is used to find the shortest path along the network between nodes.
    The walking speed is set in the config.
    Results are saved to a csv file.

    Parameters
    ----------

    access_path : str
        output path for the csv file where the accessibility data is saved.

    amenities_path : str
        path to the GeoJSON file containing the amenity data.

    buildings_path : str
        path to the GeoJSON file containing the building data.

    network_path : str
        path to the GraphML file containing the network data.

    Returns
    -------

    None
    """

    # check if an access file already exists and ask user if they want to use it or overwrite it
    if os.path.exists(access_path):
        if input('Would you like to use the existing access file? (y/n): ').strip().lower() in ['y','yes']:
            return
        else:
            print('User did not say yes to using the existing access file. The file will be overwritten.')

    # read data files
    amenities = gpd.read_file(amenities_path)
    buildings = gpd.read_file(buildings_path)
    network = ox.load_graphml(network_path)

    # remove amenities that are not in valid_amenities
    amenities = amenities[amenities['amenity'].isin(valid_amenities)].copy()

    # add a travel time attribute to every edge
    for u, v, k, data in network.edges(data=True, keys=True):
        data['time'] = data['length'] / walking_speed

    # snap buildings and amenities to network nodes, with many buildings using the same node it should run faster as there will be fewer runs
    # error will be introduced but this should be small as long as the closest node to each building isn't very far away
    building_nodes = ox.nearest_nodes(network, X=buildings.geometry.representative_point().x, Y=buildings.geometry.representative_point().y)
    amenity_nodes = ox.nearest_nodes(network, X=amenities.geometry.x, Y=amenities.geometry.y)

    # define an amenity index as a dictionary with the purpose of counting
    amenity_index = defaultdict(Counter)

    # for each amenity add a count to its closest node
    for i in range(len(amenities)):
        amenity_index[amenity_nodes[i]][amenities.iloc[i]['amenity']] += 1

    # define shared_building_nodes as dictionary containing a list
    shared_building_nodes = defaultdict(list)

    # buildings which have the same closest node are grouped in the shared_building_nodes dictionary using ids from the buildings file
    for b_index, node in enumerate(building_nodes):
        shared_building_nodes[node].append(int(buildings.iloc[b_index]['id']))

    # define all_building_results as an empty list
    all_building_results = []

    # loop through buildings and their nodes
    for origin_node, building_id in shared_building_nodes.items():

        # compute travel times from one node to all other nodes within a 60 minute walking distance using dijkstra
        travel_time = nx.single_source_dijkstra_path_length(network, origin_node, cutoff=60, weight='time')

        # create sets of nodes for 15 minutes, 30 minutes, and 60 minutes (60 minute includes all nodes reachable in the 60 minute cutoff)
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
                                     "15min": count_amenities(nodes_15, amenity_index),
                                     "30min": count_amenities(nodes_30, amenity_index),
                                     "60min": count_amenities(nodes_60, amenity_index)})

    # create a pandas data frame with the results
    df = pd.DataFrame(all_building_results)

    # save results to a csv file
    df.to_csv(access_path, index=False)
    print('Access file saved.')

# define function for calculating the score for in every scoring category for every walking distance of interest
def score_row(row):
    """
    Calculate the score for a single building using all scoring methods for 15, 30, and 60 minute walking distances.

    Parameters
    ----------

    row : pandas.Series
        row containing amenity counts for '15min', '30min', and '60min' walking distances.

    Returns
    -------

    dict
        nested dictionary structured as: {distance: {category: score}}.
    """

    return {
        '15': {k: f(row['15min']) for k, f in scorer_methods.items()},
        '30': {k: f(row['30min']) for k, f in scorer_methods.items()},
        '60': {k: f(row['60min']) for k, f in scorer_methods.items()}
    }

# define function for calculating the overall score by weighting and summing all categories (creates a weighted score out of 100 to 2 decimal places)
def main_score(s, d):
    """
    Calculate a weighted overall score for each building using their scores for each category of amenities for 15, 30, and 60 minute walking distances.

    Parameters
    ----------

    s : dict
        nested score directory created from the 'score_row' function.

    d : str
        distance key ('15', '30', or '60').

    Returns
    -------

    float
        weighted score between 0 and 100.
    """

    return round(sum(s[d][k] * weights[k] for k in weights) / total_weights * 100, 2)

# define function to flatten nested score dictionaries into a tabular form all scores for a building including group and overall scores
def flatten_scores(s):
    """
    Flatten nested score dictionaries into a tabular format.

    Parameters
    ----------

    s : dict
        nested score directory created from the 'score_row' function.

    Returns
    -------

    dict
        flattened dictionary with keys structured as: '15 Postal', '30 Banking', etc.
    """

    # define output as an empty dictionary
    output = {}

    # flatten scores for each group at 15min, 30min, 60min walking distances
    for d in ['15', '30', '60']:
        for k, v in s[d].items():
            output[f'{d} {k}'] = v

        # calculate and flatten overall scores based on the main_score function
        output[f'{d} Overall'] = main_score(s, d)
    return output

# define function for calculating the individual and overall scores for every walking distance of interest and add to the dataframe
def apply_scoring(access_path, buildings_path, output_path):
    """
    Apply scoring logic to accessibility data and export results.

    Parses stored Counter objects from csv.
    Expands rows where buildings shared the same closest node.
    Computes category and overall scores for 15, 30, and 60 minute walking distances.
    Adds scores to the buildings data and stores as a GeoJSON.

    Parameters
    ----------

    access_path : str
        path to the csv file containing the accessibility data.

    buildings_path : str
        path to the GeoJSON file containing the building data.

    output_path : str
        output path for the GeoJSON file where the scored buildings data is saved.

    Returns
    -------

    None
    """

    # read data files
    access = pd.read_csv(access_path)
    buildings = gpd.read_file(buildings_path)

    # apply parsing for each walking distance column
    for col in ['15min', '30min', '60min']:
        access[col] = access[col].apply(counter_parser)

    # apply id parsing
    access['building_id'] = access['building_id'].apply(id_parser)

    # split lists of building_ids into multiple rows of building_ids containing a single buildin_id
    access = access.explode('building_id').reset_index(drop=True)

    # calculate the for each group at each desired walking distance
    access['scores'] = access.apply(score_row, axis=1)

    # flatten nested score dictionaries into a tabular form (the function also calculates the overall scores)
    flat = pd.DataFrame(
        access['scores'].apply(flatten_scores).tolist()
    )

    # convert ids to strings
    flat['id'] = access['building_id'].astype(str)
    buildings['id'] = buildings['id'].astype(str)

    # merge based on id and add to the GeoJSON file
    output = buildings.merge(flat, on='id', how='left')
    output.to_file(output_path, driver="GeoJSON")
    print("Added scores to GeoJSON.")

# define function for selecting a subfolder from all subfolders in data/
def select_subfolder():
    """
    Display all folders within the data folder and return the path of the subfolder selected by the user.

    Returns
    -------

    subfolder : str
        path to the subfolder where all data for the location of interest is stored.
    """

    # define a list of the subfolders in data only including subfolders not the .csv data
    subfolders = [
        name for name in os.listdir('data') if os.path.isdir(os.path.join('data', name))
    ]

    # print all subfolders present in data with a number
    for i, name in enumerate(subfolders, start=1):
        print(f'{i}: {name}')

    # user selects the data they want to use by inputting the number associated with the subfolder
    while True:
        # defines subfolder based on the choice of the user
        try:
            choice = int(input("Please select which location's data you want to use (1,2,3...): "))
            if 1 <= choice <= len(subfolders):
                subfolder = 'data/' + str(subfolders[choice - 1]) + '/'
                break

            # if user inputs a number to big or small they will be reminded of the range of numbers and user will try again
            else:
                print('Please select a number between 1 and ' + str(len(subfolders)))

        # if an exception occurs (user did not input a number) an error message is displayed and user will try again
        except Exception:
            print('User did not select a number, please try again')

    # print and return the subfolder the user has selected
    print('Data will be loaded from: ' + str(subfolder))
    return subfolder

# define function for running the transform pipeline
def run_transform(subfolder):
    """
    Run the accessibility calculations and apply scoring to the data in the inputted subfolder.

    Define input and output file paths based on the subfolder.
    Compute walking accessibility to amenities for each building and save the output to a csv using the 'building_access' function.
    Apply scoring logic to accessibility data and export results as a GeoJSON using the 'apppy_scoring' function.

    Parameters
    ----------

    subfolder : str
        path to the subfolder where all data for the location of interest is stored.

    Returns
    -------

    None
    """

    # define paths to read data files
    amenities_path = os.path.join(subfolder, 'amenities.geojson')
    buildings_path = os.path.join(subfolder, 'buildings.geojson')
    network_path = os.path.join(subfolder, 'network.graphml')

    # define output paths
    access_path = os.path.join(subfolder,'buildings_access.csv')
    output_path = os.path.join(subfolder,'buildings_scored.geojson')

    # run scoring access and scoring function and save results to csv
    building_access(access_path, amenities_path, buildings_path, network_path)
    apply_scoring(access_path, buildings_path, output_path)