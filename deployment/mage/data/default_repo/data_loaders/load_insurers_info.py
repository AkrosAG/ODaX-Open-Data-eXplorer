if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test
import pandas as pd

@data_loader
def load_data_from_file(*args, **kwargs):
    """
    Loading the data from the insurances to a df

    Returns:
       dataframe 
    """
    for sheet in ["Zugelassene Krankenversicherer", "zugelassene krankenversicherer"]:
        try:
            XLS_INSURERS = '/home/src/raw_data/healthinsurance/BagNr_Mapping_KV.xlsx'
            df_insur = pd.read_excel(XLS_INSURERS, sheet_name=sheet)
            df_insur = df_insur.rename(columns=str.strip)

        except Exception:
            continue

    
    df_insurers_part = df_insur[['Nummer','Name']].rename(columns = {'Nummer':'bag_number','Name':'insurer'})
    print(df_insurers_part['bag_number'].values)
    ## filter out null value rows and rows that contain also letters instead just an int number
    mask = pd.to_numeric(df_insurers_part['bag_number'], errors = 'coerce').notna()
    df_insurers_filtered = df_insurers_part[mask]

    return df_insurers_filtered
    


@test
def test_output(output, *args) -> None:
    """
    Template code for testing the output of the block.
    """
    assert output is not None, 'The output is undefined'

