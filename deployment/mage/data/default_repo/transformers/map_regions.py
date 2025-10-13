if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test
import pandas as pd
from os import path
from mage_ai.settings.repo import get_repo_path
from mage_ai.io.postgres import Postgres
from mage_ai.io.config import ConfigFileLoader
from collections import Counter
from default_repo.utils.constants import swiss_cantons_abbr_to_name
from typing import List, Optional
import datetime
import requests
from default_repo.utils.constants import XLS_MUNIC
from io import StringIO


@transformer
def export_data(df_fr, *args, **kwargs):
    """
    Add for all the cantons and according fee regions the municipalities.

    returns:
    df with all the municipalities as well as canton_code and fee_region number
    """

    #function to get the municpalities when there are multiple fee regions for the canton
    def GetMunicipalities_PerCanton(Canton: str) -> List[str]:

        # Get today's date in DD-MM-YYYY format
        today = datetime.datetime.today().strftime("%d-%m-%Y")
        url = f"https://www.agvchapp.bfs.admin.ch/api/communes/levels?date={today}"

        headers = {"Accept": "application/json", "User-Agent": "Mozilla/5.0"}

        response = requests.get(url, headers=headers)
        try:
            data = response.json()
        except Exception:
            try:
                data = response.content.decode("latin-1")
            except Exception as e:
                logger.error("latin-1 decode also failed.")
                raise e

        df = pd.read_csv(StringIO(data))
        return df[df["Canton"] == Canton]["Name"].values.tolist()
    
    #function to get the municpalities when there is just one fee region per canton
    def GetMunicipalities_MultipleFeeRegions(Kanton: str, Region: str) -> Optional[List[str]]:

        try:
            sheet = "Anhang EDI Ver. über die PR"
            Data = pd.read_excel(XLS_MUNIC, sheet_name=sheet)
            #logger.success("✅ File loaded successfully.")
            #3if not Region.isdigit():
            #  Region = Region[-1]
            filtered = (
                Data[(Data["Kanton"] == Kanton) & (Data["Region"] == int(Region))][
                    "Gemeinde"
                ]
                .dropna()
                .unique()
            )
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


    #Filtering
    pairs = set(df_fr.keys())
    df_count = df_fr.groupby('canton_code')['region_no'].count().reset_index()
    multi_cantons = df_count[df_count['region_no']>1]['canton_code'].values
    single_cantons = df_count[df_count['region_no']==1]['canton_code'].values
    #dictionnary single cantons
    df_fr_filtered = df_fr[df_fr['canton_code'].isin(single_cantons)]
    single_pair_by_canton = dict(zip(df_fr_filtered['canton_code'], df_fr_filtered['region_no']))
    #dictionnary multi cantons
    df_fr_filtered = df_fr[df_fr['canton_code'].isin(multi_cantons)]

    # 1) Single-region cantons: call once per canton
    single_muni_by_canton: dict[str, list[str]] = {}

    for cc in single_cantons:
        rn = single_pair_by_canton[cc]
        try:
            lst = GetMunicipalities_PerCanton(swiss_cantons_abbr_to_name[cc]) or []
        except Exception:
            lst = []
        clean = sorted({str(m).strip() for m in lst if m and str(m).strip()})
        single_muni_by_canton[cc,rn] = clean

    # 2) Multi-region cantons: call once per (canton, region_no)
    muni_by_pair: dict[tuple[str, int], list[str]] = {}

    for i in range(len(df_fr_filtered)):
        cc = str(df_fr_filtered.iloc[[i]]['canton_code'].values[0])
        rn = int(df_fr_filtered.iloc[[i]]['region_no'].values[0])
        try:
            lst = GetMunicipalities_MultipleFeeRegions(cc, str(rn)) or []
        except Exception:
            lst = []
        clean = sorted({str(m).strip() for m in lst if m and str(m).strip()})
        muni_by_pair[(cc, rn)] = clean
    
    #add to a df
    records = []
    for (canton_code,region_no), municipality in muni_by_pair.items():
        for m in municipality:
            records.append({'canton_code':canton_code, 'region_no': region_no, 'municipality':m})
    
    df_muni = pd.DataFrame(records)
    
    records = []
    for (canton_code,region_no), municipality in single_muni_by_canton.items():
        for m in municipality:
            records.append({'canton_code':canton_code, 'region_no': region_no, 'municipality':m})

    df_sin = pd.DataFrame(records)
    
    df = pd.concat([df_sin, df_muni])

    return df
    
