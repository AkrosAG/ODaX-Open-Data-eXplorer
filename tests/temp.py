from imping.nabel_airquality.lib_openweathermap import get_air_quality

lat, lon, key = 46.948, 7.447, "d71cc8fc52d1a3f2fe45a1fa4d34f042"
data = get_air_quality(lat, lon, key)
f = 3
