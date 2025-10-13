import pandas as pd
from mage_ai.io.file import FileIO
if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test
from default_repo.utils.constants import swiss_cantons_abbr_to_name

@data_loader
def load_data_from_file(*args, **kwargs):
    """
    Add all the cantons to one table for later analysis
    """
    df_cantons = pd.DataFrame(swiss_cantons_abbr_to_name.items(), columns = ['canton_code','canton'])
    
    return df_cantons

@test
def test_output(output, *args) -> None:
    """
    Template code for testing the output of the block.
    """
    assert output is not None, 'The output is undefined'
