import pandas as pd
import os
import glob

if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test


@data_loader
def load_data_from_file(*args, **kwargs):
    """
    Load all pollutant data from historical_data CSV files and group by station
    """
    try:
        # Path to historical data directory
        DATA_DIR = '/home/src/raw_data/nabel/historical_data/'

        # Get all CSV files
        csv_files = glob.glob(os.path.join(DATA_DIR, '*.csv'))
        
        if not csv_files:
            raise Exception("No CSV files found in the data directory")
        
        print(f"Found {len(csv_files)} CSV files:")
        for file in csv_files:
            print(f"  - {os.path.basename(file)}")
        
        all_data = []

        for csv_file in csv_files:
            try:
                # Extract pollutant code from filename
                pollutant_code = os.path.basename(csv_file).replace('.csv', '')
                
                # Extract title and unit from CSV file
                with open(csv_file, 'r', encoding='iso-8859-1') as f:
                    lines = f.readlines()
                    
                    # Extract title from line 1
                    if len(lines) >= 1:
                        title_line = lines[0].strip()  # Line 1 (0-indexed)
                        if title_line.startswith('Schadstoff: '):
                            title = title_line.replace('Schadstoff: ', '').strip()
                            # Remove parentheses and their content
                            import re
                            title = re.sub(r'\([^)]*\)', '', title).strip()
                        else:
                            title = pollutant_code
                    else:
                        title = pollutant_code
                    
                    # Extract unit from line 3
                    if len(lines) >= 3:
                        unit_line = lines[2].strip()  # Line 3 (0-indexed)
                        if unit_line.startswith('Einheit: '):
                            unit = unit_line.replace('Einheit: ', '').strip()
                        else:
                            unit = 'unknown'
                    else:
                        unit = 'unknown'
                
                # Read CSV, skipping header lines and using line 5 as column names
                df = pd.read_csv(csv_file, sep=';', skiprows=4, encoding='iso-8859-1')
                
                # Remove empty rows
                df = df.dropna(how='all')
                
                # Skip if no data
                if df.empty:
                    print(f"  No data found in {pollutant_code}")
                    continue
                
                # Rename the first column to 'date' (it's usually 'Datum/Zeit')
                date_col = df.columns[0]
                df = df.rename(columns={date_col: 'date'})
                
                # Convert to long format (melt)
                df_melted = pd.melt(
                    df, 
                    id_vars=['date'], 
                    var_name='station', 
                    value_name='value'
                )
                
                # Add code, title and unit columns
                df_melted['code'] = pollutant_code
                df_melted['title'] = title
                df_melted['unit'] = unit
                
                # Convert date to datetime and extract date only
                df_melted['date'] = pd.to_datetime(df_melted['date'], format='%d.%m.%Y', errors='coerce').dt.date
                
                # Convert value to numeric
                df_melted['value'] = pd.to_numeric(df_melted['value'], errors='coerce')
                
                # Remove rows with missing values
                df_melted = df_melted.dropna()
                
                all_data.append(df_melted)
                
            except Exception as e:
                print(f"Error processing {csv_file}: {str(e)}")
                continue
        
        if not all_data:
            print("No data loaded!")
            return pd.DataFrame()
        
        # Combine all data
        combined_data = pd.concat(all_data, ignore_index=True)
        
        print("\n=== FINAL DATASET ===")
        print(f"Total records: {len(combined_data)}")
        print(f"Date range: {combined_data['date'].min()} to {combined_data['date'].max()}")
        print(f"Pollutants: {sorted(combined_data['code'].unique())}")
        
        # Print all unique stations
        unique_stations = sorted(combined_data['station'].unique())
        print(f"\n=== ALL UNIQUE STATIONS ({len(unique_stations)} total) ===")
        for i, station in enumerate(unique_stations, 1):
            station_count = len(combined_data[combined_data['station'] == station])
            print(f"{i:2d}. {station} ({station_count} records)")
        
        # Group by station example
        print("\n=== SAMPLE: BERN-BOLLWERK DATA ===")
        bern_data = combined_data[combined_data['station'].str.contains('Bern', case=False, na=False)]
        if not bern_data.empty:
            print(f"Bern records: {len(bern_data)}")
            print("Sample data:")
            print(bern_data.head())
            
            print("\nPollutants available for Bern:")
            print(bern_data['code'].value_counts())
        
        return combined_data
    
    except Exception as e:
        # Pipeline-level rollback: Log error and re-raise
        print(f"PIPELINE ERROR: {str(e)}")
        print("Pipeline will rollback all changes")
        
        # Log additional context for debugging
        import traceback
        print(f"📋 Error details: {traceback.format_exc()}")
        
        # Re-raise the exception to trigger Mage's rollback mechanism
        raise e


@test
def test_output(output, *args) -> None:
    """
    Template code for testing the output of the block.
    """
    assert output is not None, 'The output is undefined'
    assert len(output) > 0, 'No data was loaded'
    
    # Check required columns
    required_columns = ['date', 'station', 'code', 'title', 'value', 'unit']
    for col in required_columns:
        assert col in output.columns, f'Missing column: {col}'
    
    # Check data types
    assert output['date'].dtype == 'object', 'Date column should contain date objects'
    assert all(isinstance(d, pd.Timestamp) or hasattr(d, 'year') for d in output['date'].dropna()), 'Date column should contain date objects'
    assert pd.api.types.is_numeric_dtype(output['value']), 'Value column should be numeric'
    
    print("All tests passed!")
