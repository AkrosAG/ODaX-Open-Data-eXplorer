import requests
import numpy as np


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


def get_wgs84_municipality(name):
    url = 'https://api3.geo.admin.ch/rest/services/api/Search'
    params = {
        'searchText': name,
        'type': 'municipality',
        'limit': 1
    }
    r = requests.get(url, params=params)
    results = r.json().get('results', [])
    if results:
        geom = results[0]['attrs']
        return float(geom['easting']), float(geom['northing'])
    else:
        return None

def get_wgs84_municipality(name):
    url = 'https://api3.geo.admin.ch/rest/services/api/SearchServer'
    params = {
        'searchText': name,
        'type': 'locations',  # 'locations' is correct, not 'municipality'
        'limit': 5  # Search a few results in case of similar names
    }
    r = requests.get(url, params=params)
    r.raise_for_status()  # Raise if there is a 404 or other error
    results = r.json().get('results', [])
    for res in results:
        if res['attrs'].get('featureId') is not None:
            geom = res['attrs']
            # WGS84 latitude and longitude
            return float(geom['lat']), float(geom['lon'])
    # If no municipality found
    return None



def idw_interpolate(stations_df, target_lat, target_lon, value_col='value', k=4, power=2):
    """
    Interpolate the value at a target location using Inverse Distance Weighting (IDW).

    Parameters:
        stations_df: pd.DataFrame with columns ['lat', 'lon', value_col]
        target_lat: latitude of the target point (municipality center)
        target_lon: longitude of the target point
        value_col: name of the column containing air pollution values
        k: number of nearest stations to use (default 4)
        power: IDW power parameter (default 2)
    Returns:
        Interpolated value at (target_lat, target_lon)
    """
    # Calculate distances (approx. using Euclidean on lat/lon, for small regions)
    coords = stations_df[['WGS84_Latitude','WGS84_Longitude']].values
    dists = np.sqrt((coords[:, 0] - target_lat) ** 2 + (coords[:, 1] - target_lon) ** 2)

    # Avoid division by zero (if point coincides with a station)
    if np.any(dists == 0):
        return stations_df.loc[dists == 0, value_col].iloc[0]

    # Get indices of k nearest stations
    nearest_idx = np.argsort(dists)[:k]
    nearest_dists = dists[nearest_idx]
    nearest_values = stations_df.iloc[nearest_idx][value_col].values

    # Filter out NaN values
    valid_mask = ~np.isnan(nearest_values)
    valid_dists = nearest_dists[valid_mask]
    valid_values = nearest_values[valid_mask]

    # If no valid neighbors, return np.nan
    if len(valid_values) == 0:
        return np.nan

    # Compute weights (inverse distance)
    weights = 1 / (valid_dists ** power)
    weights /= weights.sum()

    interpolated_value = np.sum(weights * valid_values)
    return interpolated_value
