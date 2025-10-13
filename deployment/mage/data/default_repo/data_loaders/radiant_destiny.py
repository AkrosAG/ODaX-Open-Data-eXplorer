if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test
from typing import List, Optional
import datetime
import requests
import pandas as pd
from io import StringIO
from default_repo.utils.constants import XLS_MUNIC
@data_loader
def GetMunicipalities_MultipleFeeRegions() -> Optional[List[str]]:

    try:
        sheet = "Anhang EDI Ver. über die PR"
        Data = pd.read_excel(XLS_MUNIC, sheet_name=sheet)
        #logger.success("✅ File loaded successfully.")
        #3if not Region.isdigit():
          #  Region = Region[-1]
        filtered = (
            Data[(Data["Kanton"] == 'Bern') & (Data["Region"] == int(1))][
                "Gemeinde"
            ]
            .dropna()
            .unique()
        )
        print(filtered)
        return filtered.tolist()

    except FileNotFoundError:
        print(f'error file: {pth}')
    except UnicodeDecodeError as e:
        print(f'error file: {e}')
    except pd.errors.ParserError as e:
        print(f'error file: {e}')
    except Exception as e:
        print(f'error file: {e}')

    return None
