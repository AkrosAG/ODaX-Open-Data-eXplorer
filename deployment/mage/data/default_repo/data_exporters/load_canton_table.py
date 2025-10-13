if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter
from mage_ai.settings.repo import get_repo_path
from mage_ai.io.config import ConfigFileLoader
from mage_ai.io.postgres import Postgres
from os import path

@data_exporter
def export_data_to_postgres(df_cantons, **kwargs) -> None:
    """
    Exporting the data in the table "df_cantons" to the postgres database.
    """
    print(df_cantons)
    schema_name = 'public'  
    config_path = path.join(get_repo_path(), 'io_config.yaml')
    config_profile = 'postgres'

    with Postgres.with_config(ConfigFileLoader(config_path, config_profile)) as loader:
        loader.execute("TRUNCATE TABLE public.cantons RESTART IDENTITY CASCADE;")
        loader.export(
            df_cantons,
            schema_name,
            'cantons',
            index=False,
            if_exists='replace',
        )
        
        print("Cantons inserted successfully!")
