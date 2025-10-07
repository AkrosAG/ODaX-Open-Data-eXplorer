if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test


@transformer
def transform(df, df_cantons, *args, **kwargs):
    """
    Function that filters the cantons in the "Prämien.csv" File. The final df contains only canton abbreviations that are also inside the table "cantons".


    Args:
        df: The output from the upstream parent block load_prämien_info
        df_cantons: The output from the upstream parent block load_cantons
        args: The output from any additional upstream blocks (if applicable)

    Returns:
        df: Containing the Prämien.csv informations that are filtered by the according cantons.
    """
    def normalize_val(val):
        if val is None:
            return None
        s = str(val).strip()
        if not s:
            return None
        u = s.upper()
        # Prüfe 2-Buchstaben-Code
        if len(u) == 2 and u in df_cantons['canton_code'].values:
            return u
        else:
            print("Value did not fit into a canton code. The value is: ", u)

 
    df = df.copy()  # Original DataFrame unangetastet lassen
    df['Kanton'] = df['Kanton'].apply(normalize_val)

    return df



@test
def test_output(output, *args) -> None:
    """
    Template code for testing the output of the block.
    """
    assert output is not None, 'The output is undefined'