if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter
from mage_ai.settings.repo import get_repo_path
from mage_ai.io.config import ConfigFileLoader
from mage_ai.io.postgres import Postgres
from os import path
import pandas as pd
from default_repo.utils.constants import list_franchise

@data_exporter
def export_data_to_postgres(df_cantons, **kwargs) -> None:
    """
    Export the data to the franchises (fixed code) to the PostgreSQL database.
    """
    
    
    list_franchise_df = pd.DataFrame(list_franchise, columns=['amount'])
    print(list_franchise_df)

    schema_name = 'public'  
    config_path = path.join(get_repo_path(), 'io_config.yaml')
    config_profile = 'postgres'

    with Postgres.with_config(ConfigFileLoader(config_path, config_profile)) as loader:
        loader.execute("TRUNCATE TABLE public.franchises RESTART IDENTITY CASCADE;")
        loader.export(
            list_franchise_df,
            schema_name,
            'franchises',
            index=False,
            if_exists='replace',
        )
        
        print("Franchises inserted successfully!")