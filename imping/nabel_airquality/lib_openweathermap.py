"""
OpenWeatherMap Air Quality API Client

This module provides functions to interact with the OpenWeatherMap Air Quality API,
allowing retrieval of current air pollution data for any location by coordinates.
"""

import requests
from typing import Dict, Any, Optional


def get_air_quality(
    latitude: float, longitude: float, api_key: str
) -> Optional[Dict[str, Any]]:
    """
    Retrieves air quality data from OpenWeatherMap API for a specific location.

    This function queries the OpenWeatherMap Air Pollution API to get current air quality
    data for the specified coordinates. The API returns information about various pollutants
    including CO, NO, NO2, O3, SO2, PM2.5, PM10, NH3, and an Air Quality Index (AQI).

    Args:
      latitude (float): Latitude of the location in decimal degrees.
      longitude (float): Longitude of the location in decimal degrees.
      api_key (str): Your OpenWeatherMap API key for authentication.

    Returns:
      Optional[Dict[str, Any]]: A dictionary containing air quality data with the following structure:
        {
          "coord": {"lon": float, "lat": float},
          "list": [
            {
              "main": {"aqi": int},  # Air Quality Index (1-5, where 1=Good, 5=Very Poor)
              "components": {
                "co": float,  # Carbon monoxide (μg/m3)
                "no": float,  # Nitrogen monoxide (μg/m3)
                "no2": float,  # Nitrogen dioxide (μg/m3)
                "o3": float,  # Ozone (μg/m3)
                "so2": float,  # Sulphur dioxide (μg/m3)
                "pm2_5": float,  # Fine particles (μg/m3)
                "pm10": float,  # Coarse particles (μg/m3)
                "nh3": float  # Ammonia (μg/m3)
              },
              "dt": int  # Timestamp (Unix, UTC)
            }
          ]
        }
        Returns None if an error occurs during the API request.
    """
    url = f"https://api.openweathermap.org/data/2.5/air_pollution?lat={latitude}&lon={longitude}&appid={api_key}"

    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None
