if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test
from os import path
import pandas as pd
from os import path
from mage_ai.settings.repo import get_repo_path
from mage_ai.io.postgres import Postgres
from mage_ai.io.config import ConfigFileLoader
from collections import Counter
from default_repo.utils.constants import swiss_cantons_abbr_to_name
from typing import List, Optional
import datetime
import requests
from default_repo.utils.constants import XLS_MUNIC
from io import StringIO


@transformer
def transform(data, *args, **kwargs):
    """
    Code gets the fee_region_id and adds it to the municipality table

    Args:
        data: The output from the upstream parent block

    Returns:
        df ready for export
    """
        
    schema_name = 'public'  
    config_path = path.join(get_repo_path(), 'io_config.yaml')
    config_profile = 'postgres'

    with Postgres.with_config(ConfigFileLoader(config_path, config_profile)) as loader:
        df = loader.load("Select * from public.fee_regions;")
        print("Fee regions inserted successfully!")
    
    df_tot = pd.merge(data, df, on = ['canton_code', 'region_no']).drop(['region_no'], axis = 1)
    #rename for the specific table in sql
    df_tot = df_tot[['municipality','canton_code','fee_region_id']]


    return df_tot


@test
def test_output(output, *args) -> None:
    """
    Template code for testing the output of the block.
    """
    assert output is not None, 'The output is undefined'