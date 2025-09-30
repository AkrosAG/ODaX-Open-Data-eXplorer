if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test

import pandas as pd
import unicodedata


@transformer
def transform(stations_df, pollutants_df, pollutant_measurement_df, *args, **kwargs):
    """
    Transform pollutant mesuarement readings in order to be persisted to database
    """
    # Add pollutant id
    pollutant_lookup = pollutants_df[['code', 'id']].drop_duplicates().rename(columns={'id': 'pollutant_id'})
    merged = pollutant_measurement_df.merge(pollutant_lookup, on='code', how='left')

    # Add station id - normalize text to handle accented characters
    def normalize_text(text):
        """Remove accents and convert to uppercase"""
        if pd.isna(text):
            return text
        # Normalize unicode (NFD = decomposed form)
        normalized = unicodedata.normalize('NFD', str(text))
        # Remove accent marks (category 'Mn' = nonspacing marks)
        ascii_text = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
        return ascii_text.upper()

    merged['station_normalized'] = merged['station'].apply(normalize_text)
    station_lookup = stations_df[['title', 'id']].drop_duplicates().rename(columns={'id': 'station_id'})
    station_lookup['title_normalized'] = station_lookup['title'].apply(normalize_text)

    merged = merged.merge(station_lookup, left_on='station_normalized', right_on='title_normalized', how='left')

    # Rename columns to match database schema
    if 'date' in merged.columns:
        merged = merged.rename(columns={'date': 'created_at'})
    if 'value' in merged.columns:
        merged = merged.rename(columns={'value': 'reading'})

    # Convert ID columns to integers (they may be floats after merge)
    if 'pollutant_id' in merged.columns:
        merged['pollutant_id'] = merged['pollutant_id'].astype('Int64')  # nullable integer
    if 'station_id' in merged.columns:
        merged['station_id'] = merged['station_id'].astype('Int64')  # nullable integer

    # Drop source descriptive columns and duplicated title columns
    cols_to_drop = [c for c in ['code', 'title', 'title_x', 'title_y', 'title_normalized', 'unit', 'station_normalized', 'station'] if c in merged.columns]
    if cols_to_drop:
        merged = merged.drop(columns=cols_to_drop)

    return merged


@test
def test_output(output, *args) -> None:
    """
    Template code for testing the output of the block.
    """
    assert output is not None, 'The output is undefined'
