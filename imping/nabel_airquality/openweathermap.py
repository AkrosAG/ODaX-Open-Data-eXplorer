import requests
import json

def get_air_quality(latitude, longitude, api_key):
  """
  Retrieves air quality data from OpenWeatherMap API.

  Args:
    latitude: Latitude of the location.
    longitude: Longitude of the location.
    api_key: Your OpenWeatherMap API key.

  Returns:
    A JSON object containing air quality data, or None if an error occurs.
  """
  url = f"http: // api.openweathermap.org / data / 2.5 / air_pollution?lat = {latitude} & lon = {longitude} & appid = {api_key}"
  #url = f"https://api.openweathermap.org/data/2.5/air_pollution?lat={latitude}&lon={longitude}&appid={api_key}"
  url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat=50&lon=50&appid={api_key}"
  try:
    response = requests.get(url)
    response.raise_for_status()  # Raise an exception for bad status codes
    data = response.json()
    return data
  except requests.exceptions.RequestException as e:
    print(f"Error fetching data: {e}")
    return None

# Replace with your actual latitude, longitude, and API key
latitude = 47.3769
longitude = 8.5417
api_key = "d71cc8fc52d1a3f2fe45a1fa4d34f042"

air_quality_data = get_air_quality(latitude, longitude, api_key)

if air_quality_data:
  print(json.dumps(air_quality_data, indent=2))