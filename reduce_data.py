# import modules from standard library
import pandas as pd

# remove unnecessary rows and columns from csvs and save
# desired columns are id, branch_name, long_wgs84, lat_wgs84 for open banks
(
    pd.read_csv("data/geolytix_uk_open_bank_branches.csv")
    .loc[lambda df: df["status"] == "Open", ["id","branch_name","long_wgs84","lat_wgs84"]]
    .to_csv("data/geolytix_uk_open_bank_branches.csv", index = False)
)
# desired columns are id, store_name, size_band long_wgs, lat_wgs for all supermarkets
(
    pd.read_csv("data/geolytix_retailpoints_v40_202601.csv")[["id","store_name","size_band","long_wgs","lat_wgs"]]
    .to_csv("data/geolytix_retailpoints_v40_202601.csv", index = False)
)