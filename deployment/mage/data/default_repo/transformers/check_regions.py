if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test
import re


@transformer
def transform(df, *args, **kwargs):
    """
    Function that contains at the end only a reference key in the regions column. Does not contain the specific string.

    Args:
        region: The output from the upstream parent block

    Returns:
        dataframe
    """
    def parse_region_no(region):
        REGION_RX = re.compile(r"(\d+)$")  # e.g., "PR-REG CH1" -> 1
        if region is None or (isinstance(region, float) and math.isnan(region)):
            return None
        s = str(region).strip()
        m = REGION_RX.search(s)
        return int(m.group(1))

    
    df = df.copy()  # Original DataFrame unangetastet lassen
    df['Region'] = df['Region'].apply(parse_region_no)
    return df


@test
def test_output(output, *args) -> None:
    """
    Template code for testing the output of the block.
    """
    assert output is not None, 'The output is undefined'