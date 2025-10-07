if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test
import pandas as pd
from os import path
from mage_ai.settings.repo import get_repo_path
from mage_ai.io.postgres import Postgres
from mage_ai.io.config import ConfigFileLoader


@transformer
def export_data(data, *args, **kwargs):
    """
    Exporting fee regions to a PostgreSQL database.
    """
    #rename according columns:
    rows = [(c, int(r)) for c, r in data.to_records(index=False)]
    schema_name = 'public'  
    config_path = path.join(get_repo_path(), 'io_config.yaml')
    config_profile = 'postgres'

    mapping = {}
    CHUNK = 1000
    for i in range(0, len(rows), CHUNK):
        chunk = rows[i : i + CHUNK]
        values_sql = []
        params = {}
        for j, (c, r) in enumerate(chunk):
            values_sql.append(f"(:c{j}, :r{j})")
            params[f"c{j}"] = c
            params[f"r{j}"] = r
        with Postgres.with_config(ConfigFileLoader(config_path, config_profile)) as loader:
            df = loader.execute(f"""SELECT * from public.cantons;""")
            print(df)
            print("Finished!")
        
    return df 