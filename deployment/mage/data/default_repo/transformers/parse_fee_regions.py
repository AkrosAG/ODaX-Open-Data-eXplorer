if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test


@transformer
def transform(df, *args, **kwargs):
    """
    reorganize the dataframe to the wanted structure.

    Args:
        df: The output from the upstream parent block
        args: The output from any additional upstream blocks (if applicable)

    Returns:
        dataframe with fee_region number and canton_code
    """
    # Specify your transformation logic here
    df_fr = df.loc[df["Kanton"].notna() & df["Region"].notna(), ["Kanton", "Region"]]
    df_fr = df_fr.drop_duplicates()
    #rename columns
    df_fr = df_fr.rename(columns={'Kanton':'canton_code','Region':'region_no'})   

    return df_fr



@test
def test_output(output, *args) -> None:
    """
    Template code for testing the output of the block.
    """
    assert output is not None, 'The output is undefined'