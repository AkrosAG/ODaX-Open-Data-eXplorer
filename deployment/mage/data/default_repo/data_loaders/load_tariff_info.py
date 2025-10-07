if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test


@data_loader
def load_data(*args, **kwargs):
    """
    Template code for loading data from hardcoded tariff types

    Returns:
        nested list of tariff types and codes for it
    """        
    list_tariff = ("TAR-BASE", "Grundversicherung"),
        ("TAR-DIV", "Telmed/Div."),
        ("TAR-HMO", "HMO"),
        ("TAR-HAM", "Hausarztmodell")
    


    return list_tariff


@test
def test_output(output, *args) -> None:
    """
    Template code for testing the output of the block.
    """
    assert output is not None, 'The output is undefined'