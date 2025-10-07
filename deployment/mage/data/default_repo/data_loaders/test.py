if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test


@data_loader
def load_data(*args, **kwargs):
    """
    Template code for loading data from any source.

    Returns:
        Anything (e.g. data frame, dictionary, array, int, str, etc.)
    """
    XLS_INSURERS = '/home/src/raw_data/healthinsurance/BagNr_Mapping_KV.xlsx'
    df_insur = pd.read_excel(XLS_INSURERS, sheet_name=sheet)
    print(df_insur)
    return df_insur


@test
def test_output(output, *args) -> None:
    """
    Template code for testing the output of the block.
    """
    assert output is not None, 'The output is undefined'