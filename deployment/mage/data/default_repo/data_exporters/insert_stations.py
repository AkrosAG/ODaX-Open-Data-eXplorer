from mage_ai.settings.repo import get_repo_path
from mage_ai.io.config import ConfigFileLoader
from mage_ai.io.postgres import Postgres
from os import path


if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter


@data_exporter
def export_data(data, *args, **kwargs):
    """
    Export NABEL stations data to PostgreSQL database
    """
    
    if data is None or len(data) == 0:
        print("No data to export")
        return {"status": "skipped", "reason": "no_data"}
    
    print(f"Starting export of {len(data)} stations to PostgreSQL...")

    print("DataFrame columns:", list(data.columns))
    print("DataFrame shape:", data.shape)
    print("Sample data:")
    print(data.head())
    
    config_path = path.join(get_repo_path(), 'io_config.yaml')
    profile = 'postgres'

    with Postgres.with_config(ConfigFileLoader(config_path, profile)) as loader:
        # Export data
        loader.export(data, 'public', 'station', if_exists='replace', index=False, allow_reserved_words=True)
    
    print(f"Successfully exported {len(data)} stations to PostgreSQL")
    return {"status": "success", "records_exported": len(data)}