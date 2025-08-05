import requests
import numpy as np
from typing import Tuple, Optional, Union, List, Any
import pandas as pd


def swiss_lv95_to_wgs84(easting: float, northing: float) -> Tuple[Optional[float], Optional[float]]:
    """
    Convert Swiss LV95 coordinates to WGS84 coordinates using the geo.admin.ch API.
    
    Parameters:
        easting (float): The easting coordinate in the Swiss LV95 coordinate system (EPSG:2056)
        northing (float): The northing coordinate in the Swiss LV95 coordinate system (EPSG:2056)
        
    Returns:
        Tuple[Optional[float], Optional[float]]: A tuple containing (longitude, latitude) in WGS84 
        coordinate system, or (None, None) if the conversion fails
        
    Raises:
        Exceptions are caught internally and (None, None) is returned
    """
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

def parse_coords(easting_raw: Union[str, float, int], northing_raw: Union[str, float, int, None] = None) -> Tuple[Optional[float], Optional[float]]:
    """
    Parse coordinate values that may be in different formats.
    
    Handles coordinates in the following formats:
    1. Two separate numeric values (already split)
    2. A single string with format "easting/northing"
    
    Parameters:
        easting_raw (Union[str, float, int]): The easting coordinate or a string containing both coordinates
        northing_raw (Union[str, float, int, None], optional): The northing coordinate if separate from easting
        
    Returns:
        Tuple[Optional[float], Optional[float]]: A tuple containing (easting, northing) as floats,
        or (None, None) if parsing fails
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


def get_wgs84_municipality(name: str) -> Optional[Tuple[float, float]]:
    """
    Get the WGS84 coordinates (latitude, longitude) for a Swiss municipality by name.
    
    Parameters:
        name (str): The name of the municipality to search for
        
    Returns:
        Optional[Tuple[float, float]]: A tuple containing (latitude, longitude) in WGS84 
        coordinate system, or None if the municipality is not found
        
    Raises:
        Exceptions are caught internally and None is returned
    """
    url = 'https://api3.geo.admin.ch/rest/services/api/SearchServer'
    params = {
        'searchText': name,
        'type': 'locations',  # 'locations' is correct, not 'municipality'
        'limit': 5  # Search a few results in case of similar names
    }
    try:
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
    except Exception as e:
        print(f"Municipality lookup failed for {name}: {e}")
        return None



def idw_interpolate(stations_df: pd.DataFrame, target_lat: float, target_lon: float, 
                value_col: str = 'value', k: int = 4, power: int = 2) -> float:
    """
    Interpolate the value at a target location using Inverse Distance Weighting (IDW).
    
    This function uses the IDW method to estimate a value at a target location based on 
    values at nearby stations. The influence of each station decreases with distance.
    
    Parameters:
        stations_df (pd.DataFrame): DataFrame containing station data with columns 
                                   'WGS84_Latitude', 'WGS84_Longitude', and value_col
        target_lat (float): Latitude of the target point (municipality center)
        target_lon (float): Longitude of the target point
        value_col (str): Name of the column containing values to interpolate (default: 'value')
        k (int): Number of nearest stations to use in the interpolation (default: 4)
        power (int): IDW power parameter - higher values increase the influence of closer 
                    stations (default: 2)
                    
    Returns:
        float: Interpolated value at the target location. Returns np.nan if no valid 
               neighbors are found.
               
    Notes:
        - Uses Euclidean distance on lat/lon coordinates, which is an approximation 
          suitable only for small regions
        - If the target point coincides with a station, returns the value at that station
        - NaN values in the input data are filtered out
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
