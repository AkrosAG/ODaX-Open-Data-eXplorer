from dotenv import load_dotenv
import os
import json
from imping.nabel_airquality.lib_openweathermap import get_air_quality

load_dotenv()

API_KEY = os.getenv("APIKeyOpenWeatherMap")
# Replace it with your actual latitude, longitude, and API key
latitude = 47.3769
longitude = 8.5417


api_key = API_KEY

air_quality_data = get_air_quality(latitude, longitude, api_key)

if air_quality_data:
    print(json.dumps(air_quality_data, indent=2))
