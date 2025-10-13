if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter
from mage_ai.settings.repo import get_repo_path
from mage_ai.io.config import ConfigFileLoader
from mage_ai.io.postgres import Postgres
from os import path
import pandas as pd
from default_repo.utils.constants import list_age_subgroup


@data_exporter
def export_data_to_postgres(df_cantons, **kwargs) -> None:
    """
    Export the information about the age subgroup (fixed code) to the PostgreSQL database.
    """

    
    list_age_subgroup_df = pd.DataFrame(list_age_subgroup, columns=['code','label','age_class_code'])
    print(list_age_subgroup_df)

    schema_name = 'public'  
    config_path = path.join(get_repo_path(), 'io_config.yaml')
    config_profile = 'postgres'

    with Postgres.with_config(ConfigFileLoader(config_path, config_profile)) as loader:
        loader.execute("TRUNCATE TABLE public.age_subgroups RESTART IDENTITY CASCADE;")
        loader.export(
            list_age_subgroup_df,
            schema_name,
            'age_subgroups',
            index=False,
            if_exists='replace',
        )
        
        print("Age subgroup classes inserted successfully!")

