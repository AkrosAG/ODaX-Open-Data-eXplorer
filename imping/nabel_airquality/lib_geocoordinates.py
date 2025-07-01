import requests

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