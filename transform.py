# import modules
import os
import osmnx as ox
import networkx as nx
import pandas as pd
import geopandas as gpd
import math
import ast
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
    'Postal': ['post_office','post_box'],
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

# snap buildings and amenities to network nodes, with many buildings using the same node it should run faster as there will be fewer runs
# error will be introduced but this should be small as long as the closest node to each building isn't very far away
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
        "15min": count_amenities(nodes_15),
        "30min": count_amenities(nodes_30),
        "60min": count_amenities(nodes_60)})

# create a pandas data frame with the results
df = pd.DataFrame(all_building_results)

# save results to a csv file
df.to_csv(os.path.join(subfolder, 'buildings_access.csv'), index=False)

# calculating scores

# read buildings_access data file
access = pd.read_csv(os.path.join(subfolder,'buildings_access.csv'))

# define function to cover Counter() string into a dictionary
def counter_parser(s):

    # check if empty return empty if so
    if pd.isna(s):
        return {}

    # check if already formatted as a dictionary (should not be true with current storing), return if it is
    if isinstance(s,dict):
        return s

    # convert to string and remove any whitespaces at its start or end
    s = str(s).strip()

    # check if the Counter string is empty return empty if so
    if s== 'Counter()' or s == 'Counter({})':
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

    # check if id is missing (should not be the case) and return nothing if the case
    if pd.isna(d):
        return []

    # check if already a list and return it if the case
    if isinstance(d,list):
        return d

    # if a string attempt to convert into a list (list is the format it should be parsed into)
    if isinstance(d,str):
        return ast.literal_eval(d)
    return [d]

# apply parsing for each walking distance column
for col in ['15min','30min','60min']:
    access[col] = access[col].apply(counter_parser)

# apply id parsing
access['building_id'] = access['building_id'].apply(id_parser)

# split lists of building_ids into multiple rows of building_ids containing a single buildin_id
access = access.explode('building_id')

# define function to count how many distinct items are present
def count_present(counts, items):
    return sum(1 for i in items if counts.get(i, 0) > 0)

# define function which return the weight of the amenity with the highest weight
def weighted_max(counts, weights):
    return max((w for k, w in weights.items() if counts.get(k, 0) > 0), default=0)

# define function which checks if any item in a list is present
def has_any(counts, items):
    return any(counts.get(i, 0) > 0 for i in items)

# define function to constrain a value between two bounds
def clamp(x, lo=0, hi=1):
    return max(lo, min(hi, x))

# define function to apply diminishing return the greater a value is
def saturate(x, k=2):
    return 1 - math.exp(-x / k)

# define function which computes a diversity score by using the saturate function on the count_present function
def by_diversity(counts, items, k):
    return clamp(saturate(count_present(counts, items), k))

# define function for calculating a score for education
def score_education(c):

    # special case of school can be counted multiple times
    score = 0.5 * c.get('school', 0)

    # all other types: count presence only once each, only do if score is not already 1 or more
    if score < 1:
        score += 0.25 * count_present(c, ['university', 'college', 'kindergarten', 'outdoor_education_centre'])

    # return the score capped at 1
    return clamp(score)

# define food places we are happy to have multiple of
multi_food = {
    'restaurant',
    'cafe',
    'pub',
    'bar',
    'fast_food',
    'food_court'
}

# define food places where having multiple of is not any better than having one
binary_food = {
    "ice_cream",
    "vending_machine"
}

# define places that only offer water
water = {
    "water_point",
    "drinking_water"
}

# define function for calculating a score for food and drink
def score_food(c):

    # add score for each count of place in multi food
    score = sum(c.get(k,0) for k in multi_food)

    # add at most 1 score for places in binary food and 1 score if there is a water building
    score += count_present(c, binary_food)
    score += 1 if has_any(c, water) else 0

    # return score to 2 decimal places and capped at 1
    return clamp(round(saturate(score, k=2), 2))

# define weights for each market
grocery_weights = {
    "hypermarket": 1.0,
    "large_supermarket": 0.95,
    "medium_supermarket": 0.75,
    "small_supermarket": 0.5,
    "marketplace": 0.9
}

# define function for calculating a score for groceries based on highest weighted grocery amenity
def score_groceries(c):
    return weighted_max(c, grocery_weights)

# define weights for each postal place people care about
postal_weights = {
    "post_office": 1.0,
    "post_box": 0.75,
}

# define function for calculating a score for postal based on highest weighted postal amenity
def score_postal(c):
    return weighted_max(c, postal_weights)

# define function for calculating a score for banking
def score_banking(c):
    # bank dominates everything
    if c.get("bank", 0) > 0:
        return 1.0

    # start with a score of 0 if no bank
    score = 0.0

    # add specific scores based on a banking amenity being present
    if c.get("atm", 0) > 0:
        score += 0.8
    if c.get("payment_terminal", 0) > 0:
        score += 0.1
    if c.get("bureau_de_change", 0) > 0:
        score += 0.1
    if c.get("moneylender", 0) > 0 or c.get("money_lender", 0) > 0:
        score += 0.1

    # return the score capped at 1
    return clamp(score)

# define weights for religious places
religion_weights = {
    "place_of_worship": 1.0,
    "monastery": 0.5,
}

# define function for calculating a score for religion based on highest weighted religion amenity
def score_religion(c):
    return weighted_max(c, religion_weights)

# define function for calculating a score for entertainment based on the diversity of entertainment amenities rounded to 2 decimal places
def score_entertainment(c):
    return round(by_diversity(c, amenity_groups['Entertainment'], k=3), 2)

# define function for calculating a score for healthcare
def score_healthcare(c):
    # define whether clinic and doctors within walking distance
    has_clinic = c.get('clinic', 0) > 0
    has_doctors = c.get('doctors', 0) > 0

    # create a score for core healthcare facilities
    if c.get('hospital', 0) > 0:
        core = 1.0
    elif has_clinic and has_doctors:
        core = 0.9
    elif has_clinic or has_doctors:
        core = 0.5
    else:
        core = 0.0

    # create a score for supporting healthcare facilities
    support = 0.5 * (c.get('pharmacy', 0) > 0) + 0.5 * (c.get('dentist', 0) > 0)

    # return a weighted combination of core and support healthcare facilities
    return 0.7 * core + 0.3 * support

# define function for calculating a score for public services
def score_public_services(c):
    score = 0.45 * (c.get('fire_station', 0) > 0)

    # ranger station serves as a less effective police station if none present
    if c.get('police', 0) > 0:
        score += 0.45
    elif c.get('ranger_station', 0) > 0:
        score += 0.2

    # townhall and courthouse contributions are minor
    score += 0.05 * (c.get('townhall', 0) > 0)
    score += 0.05 * (c.get('courthouse', 0) > 0)

    # return score, it should be between 0 and 1
    return score

# define function for calculating a score for public transport
def score_transport(c):

    # a combination of a bus and train station dominates everything
    if c.get("train_and_bus_station", 0) > 0:
        return 1

    # start with a score of 0 if no train and bus station
    score = 0.0

    # add specific scores based on a public transport amenity being present
    if c.get("train_station", 0) > 0:
        score += 0.5
    if c.get("bus_station", 0) > 0:
        score += 0.5
    # if no bus station, bus stop is used as a less effective bus station
    elif c.get("bus_stop", 0) > 0:
            score += 0.4

    # a taxi stop or ferry terminal being within walking distance provide bonus score but are not necessary for max score
    score += 0.1 if c.get("taxi", 0) > 0 else 0
    score += 0.1 if c.get("ferry_terminal", 0) > 0 else 0

    # return the score capped at 1
    return clamp(score)

# define function for calculating a score for greenspaces based on the diversity of greenspace amenities rounded to 2 decimal places
def score_greenspace(c):
    return round(by_diversity(c, amenity_groups['Dedicated Greenspaces'], k=2), 2)

# define methods scorer will use to calculate scores per type
scorer_methods = {
    'Education': score_education,
    'Food & Drink': score_food,
    'Groceries': score_groceries,
    'Postal': score_postal,
    'Banking': score_banking,
    'Religion': score_religion,
    'Entertainment': score_entertainment,
    'Healthcare': score_healthcare,
    'Public Services': score_public_services,
    'Public Transport': score_transport,
    'Dedicated Greenspaces': score_greenspace
}

# define weights applied to each type in overall score
scorer_weights= {
    'Education': 2,
    'Food & Drink': 4,
    'Groceries': 4,
    'Postal': 1,
    'Banking': 2,
    'Religion': 1,
    'Entertainment': 3,
    'Healthcare': 3,
    'Public Services': 1,
    'Public Transport': 5,
    'Dedicated Greenspaces': 3
}

# define function for calculating the score for in every scoring category
def score_all(c):
    return {k: f(c) for k, f in scorer_methods.items()}

# define function for calculating the category scores for every walking distance of interest
def score_every_dist(row):
    return {
        '15min': score_all(row['15min']),
        '30min': score_all(row['30min']),
        '60min': score_all(row['60min']),
    }

# calculate the sum of all weights
total_weights = sum(scorer_weights.values())

# define function for calculating the overall score by weighting and summing all categories (creates a weighted score out of 100 to 2 decimal places)
def main_score(scores):
    raw_score = sum(scores[k] * scorer_weights[k] for k in scorer_weights)
    return round((raw_score / total_weights) * 100, 2)

# define function for calculating the individual and overall scores for every walking distance of interest and add to the dataframe
def apply_scoring(df):
    # apply score_all function to get each individual score
    df['15min Scores'] = df.apply(lambda row: score_all(row['15min']), axis=1)
    df['30min Scores'] = df.apply(lambda row: score_all(row['30min']), axis=1)
    df['60min Scores'] = df.apply(lambda row: score_all(row['60min']), axis=1)

    # apply the main_score function to get the overall score from the individual scores and weights and add to the dataframe
    df['15min Overall Scores'] = df['15min Scores'].apply(main_score)
    df['30min Overall Scores'] = df['30min Scores'].apply(main_score)
    df['60min Overall Scores'] = df['60min Scores'].apply(main_score)

    # return the updated dataframe
    return df

# run scoring function and save results to csv
all_scores = apply_scoring(access)
all_scores.to_csv(os.path.join(subfolder, 'buildings_scored.csv'), index=False)