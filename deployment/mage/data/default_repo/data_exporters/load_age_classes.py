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
    Exporting the information about ages classes (fixed code) to the postgres database.
    """
    list_age = [("AKL-KIN", "Kinder"),
    ("AKL-JUG", "Jugendliche"),
    ("AKL-ERW", "Erwachsene")]
    
    list_age_df = pd.DataFrame(list_age, columns=['code','label'])
    print(list_age_df)

    schema_name = 'public'  
    config_path = path.join(get_repo_path(), 'io_config.yaml')
    config_profile = 'postgres'

    with Postgres.with_config(ConfigFileLoader(config_path, config_profile)) as loader:
        loader.execute("TRUNCATE TABLE public.age_classes RESTART IDENTITY CASCADE;")
        loader.export(
            list_age_df,
            schema_name,
            'age_classes',
            index=False,
            if_exists='replace',
        )
        
        print("Age classes inserted successfully!")
