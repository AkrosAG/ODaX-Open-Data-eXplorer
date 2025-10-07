if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter
from os import path
from mage_ai.settings.repo import get_repo_path
from mage_ai.io.postgres import Postgres
from mage_ai.io.config import ConfigFileLoader


@data_exporter
def export_data(data, *args, **kwargs):
    """
    Exporting fee regions to a PostgreSQL database.
    """
    #rename according columns:
    
    schema_name = 'public'  
    config_path = path.join(get_repo_path(), 'io_config.yaml')
    config_profile = 'postgres'

    with Postgres.with_config(ConfigFileLoader(config_path, config_profile)) as loader:
        loader.execute("TRUNCATE TABLE public.fee_regions RESTART IDENTITY CASCADE;")
        loader.export(
            data,
            schema_name,
            'fee_regions',
            index=False,
            if_exists='replace',
        )
        
        print("Fee regions inserted successfully!")


