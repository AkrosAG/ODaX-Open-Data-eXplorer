import pandas as pd
import os
import time
from imping.nabel_airquality.lib_geocoordinates import parse_coords, swiss_lv95_to_wgs84
# Load the CSV
df = pd.read_csv(os.path.join('data','nabel','stations.csv'))


lats = []
lons = []

for idx, row in df.iterrows():
    easting_raw = row['Easting']
    northing_raw = row['Northing']
    easting, northing = parse_coords(easting_raw, northing_raw)
    if easting is not None and northing is not None:
        lat, lon = swiss_lv95_to_wgs84(easting, northing)
        # Respectful delay to avoid overloading the API
        time.sleep(0.3)
    else:
        lat, lon = None, None
    lats.append(lat)
    lons.append(lon)

df['WGS84_Latitude'] = lats
df['WGS84_Longitude'] = lons

# Save to new CSV
df.to_csv(os.path.join('data','nabel','stations_with_wgs84.csv'), index=False)
print('✅ Done! File written as with_wgs84.csv')
