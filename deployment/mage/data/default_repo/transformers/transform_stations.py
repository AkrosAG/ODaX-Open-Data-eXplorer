from pyproj import Transformer

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test


@transformer
def transform(data, *args, **kwargs):
    """
    Transform the station data by renaming columns, adding WGS84 coordinates, and normalizing names
    """
    
    rename_map = {
        "Station": "title",
        "Tag": "code", 
        "Easting": "lv95_easting",
        "Northing": "lv95_northing",
        "Meters_Above_Sealevel": "elevation",
        "Locationtype": "location_type",
        "Remarks": "remarks",
    }
    
    # Rename columns
    data = data.rename(columns=rename_map)

    data['title'] = data['title'].str.strip()  # Remove leading/trailing whitespace

    # Create transformer from LV95 (EPSG:2056) to WGS84 (EPSG:4326)
    coord_transformer = Transformer.from_crs('EPSG:2056', 'EPSG:4326', always_xy=True)
    
    # Convert coordinates - with always_xy=True, returns (longitude, latitude)
    longitudes, latitudes = coord_transformer.transform(
        data['lv95_easting'].values, 
        data['lv95_northing'].values
    )
    
    # Add WGS84 coordinate columns
    data['wgs84_lat'] = latitudes
    data['wgs84_lon'] = longitudes
    
    return data


@test
def test_output(output, *args) -> None:
    """
    Test the output of the transformation
    """
    assert output is not None, 'The output is undefined'
    assert len(output) > 0, 'The output DataFrame is empty'
    
    # Check that coordinate columns exist
    required_columns = ['title', 'code', 'lv95_easting', 'lv95_northing', 
                      'wgs84_lat', 'wgs84_lon', 'elevation', 'location_type']
    
    for col in required_columns:
        assert col in output.columns, f'Column {col} is missing from output'
    