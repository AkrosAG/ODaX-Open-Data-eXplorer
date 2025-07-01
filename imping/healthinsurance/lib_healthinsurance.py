from typing import Optional, List, Tuple
import pandas as pd
import requests
from io import StringIO
import datetime


def LoadData(pth: str) -> Optional[pd.DataFrame]:
    """
    Loads a CSV file with semicolon separator and Latin-1 encoding.

    Parameters:
        pth (str): The full file path to the CSV file.

    Returns:
        Optional[pd.DataFrame]: The loaded DataFrame if successful, otherwise None.

    Exceptions:
        Handles and prints informative messages for:
        - FileNotFoundError: If the file does not exist.
        - UnicodeDecodeError: If encoding fails.
        - pd.errors.ParserError: If pandas cannot parse the CSV.
        - Any other unexpected exception.
    """
    try:
        Data = pd.read_csv(pth, sep=';', encoding='latin1')
        print("✅ File loaded successfully.")
        return Data
    except FileNotFoundError:
        print(f"❌ File not found: {pth}")
    except UnicodeDecodeError as e:
        print(f"❌ Encoding error while reading the file: {e}")
    except pd.errors.ParserError as e:
        print(f"❌ Error while parsing the CSV file: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

    return None


def GetRegion(Data: pd.DataFrame, Kanton: str) -> Optional[List[str]]:
    """
    Returns a list of distinct regions for the given canton.

    Parameters:
        Data (pd.DataFrame): The input DataFrame containing at least 'Kanton' and 'Region' columns.
        Kanton (str): The name of the canton to filter by.

    Returns:
        Optional[List[str]]: A list of distinct region names if found, otherwise None.
    """
    if 'Kanton' not in Data.columns or 'Region' not in Data.columns:
        print("❌ Columns 'Kanton' or 'Region' not found in DataFrame.")
        return None

    regions = Data[Data['Kanton'] == Kanton]['Region'].dropna().unique()

    if len(regions) == 0:
        return None
    return regions.tolist()


def GetMunicipalities_MultipleFeeRegions(pth: str, Kanton: str, Region: str) -> Optional[List[str]]:
    """
    Loads a municipality list from an Excel file and returns distinct municipalities (Gemeinden)
    for a given canton and region.

    Parameters:
        pth (str): The path to the Excel file.
        Kanton (str): The canton abbreviation to filter by (e.g., 'ZH').
        Region (str): The region identifier. The function uses the last character (as a digit) to filter.

    Returns:
        Optional[List[str]]: A list of unique municipality names for the specified canton and region,
        or None if an error occurs.

    Notes:
        - Expects the Excel file to have a sheet named 'Anhang EDI Ver. über die PR'.
        - The relevant columns must include 'Kanton', 'Region', and 'Gemeinde'.
    """
    try:
        sheet = 'Anhang EDI Ver. über die PR'
        Data = pd.read_excel(pth, sheet_name=sheet)
        print("✅ File loaded successfully.")

        filtered = Data[
            (Data['Kanton'] == Kanton) &
            (Data['Region'] == int(Region[-1]))
            ]['Gemeinde'].dropna().unique()

        return filtered.tolist()

    except FileNotFoundError:
        print(f"❌ File not found: {pth}")
    except UnicodeDecodeError as e:
        print(f"❌ Encoding error while reading the file: {e}")
    except pd.errors.ParserError as e:
        print(f"❌ Error while parsing the file: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

    return None

def GetMunicipalities_PerCanton(Canton: str) -> pd.DataFrame:
    # Get today's date in DD-MM-YYYY format
    today = datetime.datetime.today().strftime("%d-%m-%Y")

    # Construct the URL
    url = f"https://www.agvchapp.bfs.admin.ch/api/communes/levels?date={today}"

    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(url, headers=headers)
    try:
        # Try utf-8 first
        data = response.json()
    except Exception:
        # Try latin-1
        try:
            data = response.content.decode("latin-1")
        except Exception as e:
            print("latin-1 decode also failed.")
            raise e
        # Try parsing as JSON after latin-1 decode (if content is actually JSON)

    df = pd.read_csv(StringIO(data))
    return df[df["Canton"] == Canton]["Name"].values.tolist()



def GetKantonRegionFromGemeinde(pth: str, Gemeinde: str) -> Optional[Tuple[str, str]]:
    """
    Looks up the canton and region for a given municipality (Gemeinde).

    Parameters:
        pth (str): The path to the Excel file.
        Gemeinde (str): The name of the municipality to search for.

    Returns:
        Optional[Tuple[str, str]]: A tuple (Kanton, Region) if found, otherwise None.

    Notes:
        - The Excel sheet must be named 'Anhang EDI Ver. über die PR'.
        - The relevant columns must include 'Gemeinde', 'Kanton', and 'Region'.
    """
    try:
        sheet = 'Anhang EDI Ver. über die PR'
        Data = pd.read_excel(pth, sheet_name=sheet)
        print("✅ File loaded successfully.")

        # Filter for matching Gemeinde (case-insensitive and stripping whitespace)
        match = Data[Data['Gemeinde'].str.strip().str.lower() == Gemeinde.strip().lower()]

        if match.empty:
            print(f"⚠️ Gemeinde '{Gemeinde}' not found.")
            return None

        # Take first match in case of duplicates
        kanton = match.iloc[0]['Kanton']
        region = str(match.iloc[0]['Region'])
        return kanton, region

    except FileNotFoundError:
        print(f"❌ File not found: {pth}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

    return None


def GetFeesByParameters(
    Data: pd.DataFrame,
    Kanton,
    Region,
    Altersklasse,
    Unfalldeckung,
    Franchise,
    Tariftyp,
    Altersgruppe=''
) -> pd.DataFrame:
    """
    Filters health insurance data for a specific region and criteria.

    Args:
        Data (pd.DataFrame): The full DataFrame to filter.
        Kanton: The canton to select.
        Region: The region within the canton.
        Altersklasse: The age class (e.g., 'AKL-KIN', 'AKL-ERW').
        Unfalldeckung: Accident coverage flag/column value.
        Franchise: The deductible value (e.g., 300, 2500).
        Tariftyp: The tariff type (e.g., 'Standard', 'Hausarztmodell').
        Altersgruppe: (Optional) The specific child/youth age subgroup.

    Returns:
        pd.DataFrame: Filtered DataFrame matching all the criteria.
    """
    # Ensure all required columns exist
    required_columns = [
        'Kanton', 'Region', 'Unfalleinschluss', 'Altersklasse',
        'Franchise', 'Tariftyp', 'Altersuntergruppe'
    ]
    missing = [col for col in required_columns if col not in Data.columns]
    if missing:
        raise ValueError(f"Missing columns in DataFrame: {missing}")

    # Filter step by step for clarity and debugging
    filtered = Data[
        (Data['Kanton'] == Kanton) &
        (Data['Region'] == Region) &
        (Data['Unfalleinschluss'] == Unfalldeckung) &
        (Data['Altersklasse'] == Altersklasse) &
        (Data['Franchise'] == Franchise) &
        (Data['Tariftyp'] == Tariftyp)
    ]

    # Apply Altersuntergruppe filter only for children, if specified
    if Altersklasse == 'AKL-KIN' and Altersgruppe != '':
        filtered = filtered[filtered['Altersuntergruppe'] == Altersgruppe]

    # Optionally: reset index for neatness
    return filtered.reset_index(drop=True)



def GetAlterunterGruppenProVersicherer(
    Data: pd.DataFrame,
    Kanton,
    Region,
    Altersklasse,
    Unfalldeckung,
    Franchise,
    Tariftyp
) -> dict:
    """
    Returns a dictionary mapping each insurer (BAG-Nummer) to a sorted list of Altersuntergruppen,
    based on the given filtering criteria.

    Args:
        Data (pd.DataFrame): The input DataFrame.
        Kanton: The canton to filter.
        Region: The region to filter.
        Altersklasse: The age class ('AKL-KIN' for children, etc.).
        Unfalldeckung: Accident coverage flag/column value.
        Franchise: The deductible.
        Tariftyp: The tariff type.

    Returns:
        dict: {Versicherer: [sorted Altersuntergruppe, ...], ...}
    """
    required_columns = [
        'Kanton', 'Region', 'Unfalleinschluss', 'Franchise', 'Tariftyp',
        'Altersklasse', 'Versicherer', 'Altersuntergruppe'
    ]
    missing = [col for col in required_columns if col not in Data.columns]
    if missing:
        raise ValueError(f"Missing columns in DataFrame: {missing}")

    filtered = Data[
        (Data['Kanton'] == Kanton) &
        (Data['Region'] == Region) &
        (Data['Unfalleinschluss'] == Unfalldeckung) &
        (Data['Franchise'] == Franchise) &
        (Data['Tariftyp'] == Tariftyp) &
        (Data['Altersklasse'] == Altersklasse)
    ]

    # Group by Versicherer and collect unique, sorted Altersuntergruppe values
    result = (
        filtered.groupby('Versicherer')['Altersuntergruppe']
        .apply(lambda x: sorted(set(x)))
        .to_dict()
    )

    return result


def GetKVNameFromBAGNumber(BAGNumber: int, pth: str) -> str:
    """
    Returns the health insurer's name corresponding to a BAG number.

    Args:
        BAGNumber (int): The BAG number to look up.
        pth (str): Path to the Excel file.

    Returns:
        str: The name of the insurer, or None if not found.
    """
    sheet_names = ['Zugelassene Krankenversicherer', 'zugelassene krankenversicherer']
    for Sheet in sheet_names:
        try:
            Data = pd.read_excel(pth, sheet_name=Sheet)
            print(f"✅ File loaded successfully (Sheet: {Sheet}).")
            if 'Nummer' in Data.columns and 'Name' in Data.columns:
                result = Data.loc[Data['Nummer'] == BAGNumber, 'Name']
                if not result.empty:
                    return result.iloc[0].strip()
                else:
                    print(f"❌ BAG number {BAGNumber} not found in the file.")
                    return None
            else:
                print("❌ Columns 'Nummer' and/or 'Name' not found in the sheet.")
        except ValueError:
            continue  # Try the next possible sheet name
        except Exception as e:
            print(f"❌ Error loading file/sheet: {e}")
            return None
    print(f"❌ None of the possible sheets found in the file.")
    return None
