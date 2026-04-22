# import modules from standard library
import math

# import local modules
from config import amenity_groups

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