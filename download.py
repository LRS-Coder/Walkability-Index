# import modules
import os
import osmnx as ox
import tempfile
import webbrowser

# define function for ensuring location is giving the correct boundary
def osm_download_confirm():

    # user inputs locations until satisfied with the boundary they would be downloading
    while True:

        # user inputs a location
        location = input("Enter a location (e.g. Paris, France): ")

        # download boundary
        boundary = ox.geocode_to_gdf(location)

        # create a temporary file to for folium image
        with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as tf:
            temp_path = tf.name

        # plot boundary on map
        m = boundary.explore(color='black')
        m.save(temp_path)

        # display boundary plot in browser and ask whether boundary is satisfactory
        webbrowser.open(f'file://{temp_path}')
        satisfied = False
        while True:
            satisfactory = input('Is this area satisfactory? (yes/no/exit): ').strip().lower()

            # act on decision
            if satisfactory in ['y','yes']:
                print('User is satisfied with the boundary.')
                satisfied = True
                break
            elif satisfactory in ['n','no']:
                print('User is NOT satisfied with the boundary.')
                break
            elif satisfactory in ['e','exit','q','quit']:
                print('User chose to exit.')
                return None
            else:
                print("Invalid Input. Please type 'yes', 'no', or 'exit'.")

        # delete the temporary file
        os.remove(temp_path)

        # download all additional data if satisfied with boundary
        if satisfied:
            osm_download_all(location)
            break

# define function for downloading from all required data from OpenStreetMaps
def osm_download_all(location, folder="data"):

    # formats the location name for use a filename
    location_filename = location.replace(",", "").replace(" ", "_")

    # download buildings, amenities, and walking network
    buildings = ox.features_from_place(location, tags = {"building": True})
    amenities = ox.features_from_place(location, tags = {"amenity": True})
    network = ox.graph.graph_from_place(location, network_type = "walk")

    # project to appropriate crs and save data
    # define target crs from network for buildings and amenities to match
    network_proj = ox.project_graph(network)
    target_crs = network_proj.graph['crs']
    # convert crs of buildings and amenities to match network
    buildings_proj = buildings.to_crs(target_crs)
    amenities_proj = amenities.to_crs(target_crs)
    # save buildings
    buildings_file = os.path.join(folder, f"{location_filename}_buildings.geojson")
    buildings_proj.to_file(buildings_file, driver = "GeoJSON")
    # save amenities
    amenities_file = os.path.join(folder, f"{location_filename}_amenities.geojson")
    amenities_proj.to_file(amenities_file, driver = "GeoJSON")
    # save walking network
    network_file = os.path.join(folder, f"{location_filename}_network.graphml")
    ox.save_graphml(network_proj, network_file)

osm_download_confirm()