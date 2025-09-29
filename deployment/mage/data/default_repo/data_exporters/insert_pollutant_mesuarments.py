from mage_ai.settings.repo import get_repo_path
from mage_ai.io.config import ConfigFileLoader
from mage_ai.io.postgres import Postgres
from pandas import DataFrame
from os import path

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter


@data_exporter
def export_data(df, *args, **kwargs):
    """
    Insert pollutant measurements into the database.
    """
    schema_name = 'public'  
    config_path = path.join(get_repo_path(), 'io_config.yaml')
    config_profile = 'postgres'

    print(f"\n=== INSERTING POLLUTANT MEASUREMENTS ===")
    print(f"Total records to insert: {len(df)}")
    print(f"Columns: {list(df.columns)}")
    print(f"Sample data:\n{df.head()}")

    with Postgres.with_config(ConfigFileLoader(config_path, config_profile)) as loader:
        # Clear existing data
        loader.execute("TRUNCATE TABLE public.pollutant_measurement RESTART IDENTITY CASCADE;")
        print("Cleared existing pollutant measurements")
        
        # Insert new data
        loader.export(
            df,
            schema_name,
            'pollutant_measurement',
            index=False,
            if_exists='append',
        )
        
        print(f" Successfully inserted {len(df)} pollutant measurements!")

