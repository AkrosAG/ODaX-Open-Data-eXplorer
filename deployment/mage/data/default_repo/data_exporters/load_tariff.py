if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter
from mage_ai.settings.repo import get_repo_path
from mage_ai.io.config import ConfigFileLoader
from mage_ai.io.postgres import Postgres
from os import path
import pandas as pd

@data_exporter
def export_data_to_postgres(df_cantons, **kwargs) -> None:
    """
    Saving the information about the tariffs (fixed code) to the postgres database.
    """
    list_tariff = [("TAR-BASE", "Grundversicherung"),
    ("TAR-DIV", "Telmed/Div."),
    ("TAR-HMO", "HMO"),
    ("TAR-HAM", "Hausarztmodell")]
    
    list_tariff_df = pd.DataFrame(list_tariff, columns=['code','label'])
    print(list_tariff_df)

    schema_name = 'public'  
    config_path = path.join(get_repo_path(), 'io_config.yaml')
    config_profile = 'postgres'

    with Postgres.with_config(ConfigFileLoader(config_path, config_profile)) as loader:
        loader.execute("TRUNCATE TABLE public.tariff_types RESTART IDENTITY CASCADE;")
        loader.export(
            list_tariff_df,
            schema_name,
            'tariff_types',
            index=False,
            if_exists='replace',
        )
        
        print("Tarrif types inserted successfully!")
