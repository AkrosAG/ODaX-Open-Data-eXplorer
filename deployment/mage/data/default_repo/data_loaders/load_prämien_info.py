import pandas as pd
import os
if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test
from default_repo.utils.constants import CSV_FEES


@data_loader
def load_data(*args, **kwargs):
    """
    Load the data from the file "Prämien_CH.csv"

    Returns:
        dataframe
    """

    df = pd.read_csv(CSV_FEES, sep=";", encoding="latin1").rename(columns=str.strip)
    df = df.rename(columns=str.strip)
    
    return df


@test
def test_output(output, *args) -> None:
    """
    Template code for testing the output of the block.
    """
    assert output is not None, 'The output is undefined'