import pandas as pd
import requests
import time
import os

def swiss_lv95_to_wgs84(easting, northing):
    url = "https://geodesy.geo.admin.ch/reframe/lv95towgs84"
    params = {
        "easting": easting,
        "northing": northing,
        "format": "json"
    }
    try:
        resp = requests.get(url, params=params, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        return data['easting'], data['northing']
    except Exception as e:
        print(f"Conversion failed for {easting}, {northing}: {e}")
        return None, None

def parse_coords(easting_raw, northing_raw):
    """
    Handles 'easting/northing' in a single field or separate columns.
    """
    # Case: both are numeric (already split)
    try:
        return float(easting_raw), float(northing_raw)
    except ValueError:
        # Try splitting if easting_raw contains '/'
        if isinstance(easting_raw, str) and '/' in easting_raw:
            east, north = easting_raw.split('/')
            try:
                return float(east), float(north)
            except Exception:
                return None, None
        return None, None

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
