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
                      'music_school','dancing_school','escape_game','fishing','hackerspace','hookah_lounge','horse_riding'],
    'Healthcare': ['dentist','pharmacy','doctors','clinic','hospital'],
    'Public Services': ['fire_station','police','townhall','courthouse','ranger_station'],
    'Public Transport': ['taxi','bus_stop','bus_station','train_station','train_and_bus_station','ferry_terminal'],
    'Dedicated Greenspaces': ['pitch','park','playground','garden','track','firepit','grave_yard','nature_reserve','dog_park']
}

# define the amenities that are valid based on if they are in amenity_groups
valid_amenities = set(a for group in amenity_groups.values() for a in group)

# define walking speed
walking_speed = 81 # metres per minute (1.35m/s)
max_walk_time = 60 # minutes

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