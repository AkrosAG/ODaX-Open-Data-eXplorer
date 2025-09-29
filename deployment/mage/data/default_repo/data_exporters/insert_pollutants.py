from mage_ai.settings.repo import get_repo_path
from mage_ai.io.config import ConfigFileLoader
from mage_ai.io.postgres import Postgres
from pandas import DataFrame
from os import path

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter


@data_exporter
def export_data_to_postgres(pollutant_df, **kwargs) -> None:
    """
    Template for exporting data to a PostgreSQL database.
    """
    schema_name = 'public'  
    config_path = path.join(get_repo_path(), 'io_config.yaml')
    config_profile = 'postgres'


    # Extract unique pollutants with their code, title and unit
    pollutants_info = pollutant_df[['code', 'title', 'unit']].drop_duplicates()
    print(f"\n=== UNIQUE POLLUTANTS TO INSERT ===")
    print(pollutants_info)

    with Postgres.with_config(ConfigFileLoader(config_path, config_profile)) as loader:
        loader.execute("TRUNCATE TABLE public.pollutant RESTART IDENTITY CASCADE;")
        loader.export(
            pollutants_info,
            schema_name,
            'pollutant',
            index=False,
            if_exists='replace',
        )
        print("Pollutants inserted successfully!")