import requests
import numpy as np
from typing import Tuple, Optional, Union
import pandas as pd
from loguru import logger


def swiss_lv95_to_wgs84(
    easting: float, northing: float
) -> Tuple[Optional[float], Optional[float]]:
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
    params = {"easting": easting, "northing": northing, "format": "json"}
    try:
        resp = requests.get(url, params=params, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        return data["easting"], data["northing"]
    except Exception as e:
        # Keep docstring; switch print -> loguru
        logger.error(f"Conversion failed for {easting}, {northing}: {e}")
        # If you want stack traces, use: logger.exception(...)
        return None, None


def parse_coords(
    easting_raw: Union[str, float, int, None],
    northing_raw: Union[str, float, int, None] = None,
) -> Tuple[Optional[float], Optional[float]]:
    """
    Accept either:
      1) a single string "easting/northing", or
      2) two separate numeric values (both must be present).
    Returns (None, None) if parsing fails or if one value is missing.
    """
    # Case A: Single string "easting/northing"
    if isinstance(easting_raw, str) and "/" in easting_raw:
        east_str, north_str = easting_raw.split("/", 1)
        try:
            return float(east_str.strip()), float(north_str.strip())
        except (ValueError, TypeError):
            return None, None

    # Case B: Both separate values must be present
    if easting_raw is None and northing_raw is None:
        return None, None
    if (easting_raw is None) ^ (northing_raw is None):
        # exactly one missing → treat as invalid pair
        return None, None

    # Case C: Both provided → try to parse
    try:
        return float(easting_raw), float(northing_raw)  # type: ignore[arg-type]
    except (ValueError, TypeError):
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
    url = "https://api3.geo.admin.ch/rest/services/api/SearchServer"
    params = {
        "searchText": name,
        "type": "locations",  # 'locations' is correct, not 'municipality'
        "limit": 5,  # Search a few results in case of similar names
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()  # Raise if there is a 404 or other error
        results = r.json().get("results", [])
        for res in results:
            if res["attrs"].get("featureId") is not None:
                geom = res["attrs"]
                # WGS84 latitude and longitude
                return float(geom["lat"]), float(geom["lon"])
        # If no municipality found
        return None
    except Exception as e:
        # Keep docstring; switch print -> loguru
        logger.error(f"Municipality lookup failed for {name}: {e}")
        # If you want stack traces, use: logger.exception(...)
        return None


def idw_interpolate(
    stations_df: pd.DataFrame,
    target_lat: float,
    target_lon: float,
    value_col: str = "value",
    k: int = 4,
    power: int = 2,
) -> float:
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
    coords = stations_df[["WGS84_Latitude", "WGS84_Longitude"]].values
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
    weights = 1 / (valid_dists**power)
    weights /= weights.sum()

    interpolated_value = np.sum(weights * valid_values)
    return float(interpolated_value)
