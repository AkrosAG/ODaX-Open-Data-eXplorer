import requests

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
  url = f"https://api.openweathermap.org/data/2.5/air_pollution?lat={latitude}&lon={longitude}&appid={api_key}"

  try:
    response = requests.get(url)
    response.raise_for_status()  # Raise an exception for bad status codes
    data = response.json()
    return data
  except requests.exceptions.RequestException as e:
    print(f"Error fetching data: {e}")
    return None
