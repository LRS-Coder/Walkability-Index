# import modules
import os
import osmnx as ox

# define location and storage folder
location = "Bushmills, Northern Ireland"
folder = "data"

# formats the location name for use a filename
location_filename = location.replace(",", "").replace(" ", "_")

# download boundary, buildings, amenities, and walking network
boundary = ox.geocode_to_gdf(location)
buildings = ox.features_from_place(location, tags = {"building": True})
amenities = ox.features_from_place(location, tags = {"amenity": True})
network = ox.graph.graph_from_place(location, network_type = "walk")

# project to appropriate crs and save data
# define target crs from network for buildings and amenities to match
network_proj = ox.project_graph(network)
target_crs = network_proj.graph['crs']
# convert crs of boundary, buildings and amenities to match network
boundary_proj = boundary.to_crs(target_crs)
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

# plot boundary on map
m = boundary_proj.explore(name='boundary', color='black')
m.save('boundary.html')