# %%
import pandas as pd
from dotenv import load_dotenv
import os
import json
from imping.healthinsurance.lib_healthinsurance import (
    LoadData,
    GetFeesByParameters,
    GetKVNameFromBAGNumber,
    GetAlterunterGruppenProVersicherer,
    GetRegion,
    GetKantonRegionFromGemeinde,
    GetMunicipalities_MultipleFeeRegions,
)
from imping.nabel_airquality.lib_openweathermap import get_air_quality
from imping.nabel_airquality.lib_geocoordinates import (
    get_wgs84_municipality,
    idw_interpolate,
)
import statistics
import numpy as np
import plotly.express as px
# %% md
#
# %%
from imping.healthinsurance.lib_healthinsurance import GetMunicipalities_PerCanton

# %% md
#  # Analysis of the health insurance data
# %% md
#  ## Insurances in Switzerland
#  First, we outline the health insurance data from the Bundesamt für Gesundheit (BAG) published over opendataswiss.
# %%
swiss_cantons_abbr_to_name = {
    "AG": "Aargau",
    "AR": "Appenzell Ausserrhoden",
    "AI": "Appenzell Innerrhoden",
    "BL": "Basel-Landschaft",
    "BS": "Basel-Stadt",
    "BE": "Bern",
    "FR": "Freiburg",
    "GE": "Genf",
    "GL": "Glarus",
    "GR": "Graubünden",
    "JU": "Jura",
    "LU": "Luzern",
    "NE": "Neuenburg",
    "NW": "Nidwalden",
    "OW": "Obwalden",
    "SH": "Schaffhausen",
    "SZ": "Schwyz",
    "SO": "Solothurn",
    "SG": "St. Gallen",
    "TI": "Tessin",
    "TG": "Thurgau",
    "UR": "Uri",
    "VD": "Waadt",
    "VS": "Wallis",
    "ZG": "Zug",
    "ZH": "Zürich",
}
# %% md
# First, we need to load the data.
# %%
# Path to the file containing the health insurance data
pth_Fees = os.path.join(os.getcwd(), "data", "healthinsurance", "Prämien_CH.csv")
Data = LoadData(pth_Fees)
# %% md
# To get an overview of which fee regions for health insurances exist in Switzerland, please run the following cell:
# %%
if Data is not None:
    for Kanton in swiss_cantons_abbr_to_name.keys():
        s_Region = GetRegion(Data, Kanton)
        if isinstance(s_Region, (list, set)):
            s_Region = ", ".join(str(region) for region in s_Region)
        print(f"Kanton {Kanton} has the regions: {s_Region}")
# %% md
# The following code outputs which municipalities belong to the fee region PR-REG CH0 of the canton Bern (BE). If you are interested in another fee region or canton, feel free to adjust the sample code.
# Knowing which municipality is in a fee region enables to detect the extrapolated air pollution as demonstrated later on in this notebook.
# %%
Canton = "BS"

if Data is not None:
    s_Region = GetRegion(Data, Canton)
    pth_Municipality = os.path.join(
        os.getcwd(), "data", "healthinsurance", "praemienregionen-ab-2025.xlsx"
    )
    if len(s_Region) > 1:
        s_Municipality = GetMunicipalities_MultipleFeeRegions(
            pth_Municipality, Canton, s_Region[0]
        )
        # Finding the canton and fee region based on the name of the municipality can be achieved by the following command:
        Kanton, Region = GetKantonRegionFromGemeinde(
            pth_Municipality, s_Municipality[0]
        )
        print(
            f"For municipality {s_Municipality[0]}, the canton is {Kanton} and the fee region is {Region}."
        )
    else:
        s_Municipality = GetMunicipalities_PerCanton(swiss_cantons_abbr_to_name[Canton])
    print(
        f"In the fee region in Canton {Canton}, the municipalities belong to: {s_Municipality}"
    )
# %% md
# In Switzerland, there are three age groups, i.e., the group for children AKL-KIN, the group for young adults AKL-JUG, and the group for adults over 25 years AKL-ERW.
# %%
s_Altersklasse = ["AKL-KIN", "AKL-JUG", "AKL-ERW"]
# %% md
# Further, when being employed in Switzerland, the employer provides the accident insurance. To avoid being insured twice, the accident insurance can be excluded from the health insurance model.
# %%
s_Unfalldeckung = ["MIT-UNF", "OHN-UNF"]
# %% md
# The third option to customize the health insurance model is the franchise. For each age group, there are several franchise options available.
# %%
vk_Franchise = {
    "AKL-KIN": [
        "FRA-0",
        "FRA-100",
        "FRA-200",
        "FRA-300",
        "FRA-400",
        "FRA-500",
        "FRA-600",
    ],
    "AKL-JUG": ["FRA-300", "FRA-500", "FRA-1000", "FRA-1500", "FRA-2000", "FRA-2500"],
    "AKL_ERW": [
        "FRA-0",
        "FRA-100",
        "FRA-200",
        "FRA-300",
        "FRA-400",
        "FRA-500",
        "FRA-600",
        "FRA-1000",
        "FRA-1500",
        "FRA-2000",
        "FRA-2500",
    ],
}
# %% md
# Moreover, there is a model called "Hausarztmodel" (TAR-HAM), which requires consulting a particular general
# practitioner before further treatment. Another model requires visiting a health maintainance organization (TAR-HMO)
# before further treatment is possible. The TAR-BASE is the "Grundversicherung" and allows to choose the physician freely.
# The model TAR-DIV requires a telemedical consultations before any further treatment.
# %%
s_Tariftyp = ["TAR-BASE", "TAR-DIV", "TAR-HMO", "TAR-HAM"]
# %% md
# When considering the health insurance for children, there are even different subgroups available depending on the
# number of siblings a child has. To receive this information for all insurance companies and a certain canton and fee
# region, the following command can be used:
# %%
Region = "1"
Kanton = "BE"
vk_Altersuntergruppe = GetAlterunterGruppenProVersicherer(
    Data,
    Kanton=Kanton,
    Region="PR-REG CH" + Region,
    Altersklasse=s_Altersklasse[0],
    Unfalldeckung=s_Unfalldeckung[0],
    Franchise=vk_Franchise[s_Altersklasse[0]][0],
    Tariftyp=s_Tariftyp[0],
)
if vk_Altersuntergruppe:
    print("Altersuntergruppen per Versicherer for your selection:")
    for versicherer, altersgruppen in vk_Altersuntergruppe.items():
        print(f"- Versicherer {versicherer}: Altersuntergruppen {altersgruppen}")
else:
    print("No Altersuntergruppen found for the selected criteria.")
# %% md
# Note, that the K1 model is for only children, the model with the highest number is for children with at least two
# siblings. If there is another model with a number in between K1 and the highest model, it is for children with one
# sibling. So, for the insurance company with BAG number 1542, the K1 model is for only children, the K4 for children
# with one sibling, and the K5 model for chlidren with at least two siblings.
# %% md
# The BAG number is a unique number, the Bundesamt für Gesundheit uses to identify an insurance company. To receive the
# name of the insurance company in Gemran, French, and Italian based on this number, the following code can be used:
# %%
pth_BAGMapping = os.path.join(
    os.getcwd(), "data", "healthinsurance", "BagNr_Mapping_KV.xlsx"
)
BAG_Number = 8
Name_HealthinInsurance = GetKVNameFromBAGNumber(8, pth_BAGMapping)
print(f"The insurer for BAG number {BAG_Number} is: {Name_HealthinInsurance}")

# %% md
# If you are interested in determining the health insurance fees for a certain insurance model, then execute the
# following code, which returns you all insurance fees of all insurance companies whose insurances fit your
# specifications:
# %%
AltersGruppe = vk_Altersuntergruppe[BAG_Number][0]
Fees = GetFeesByParameters(
    Data=Data,
    Kanton=Kanton,
    Region="PR-REG CH" + Region,
    Altersklasse=s_Altersklasse[0],
    Unfalldeckung=s_Unfalldeckung[0],
    Franchise=vk_Franchise[s_Altersklasse[0]][0],
    Tariftyp=s_Tariftyp[0],
    Altersgruppe=AltersGruppe,
)
print(Fees)
# %% md
# To receive the specific fee for a certain insurance company, then filter the fees by the BAG number as following:
# %%
FeePerInsurance = Fees[Fees["Versicherer"] == BAG_Number]
print(FeePerInsurance)
# %% md
# ## Analysis of the air quality data
# %% md
# First, we focus on the air quality data from the Nationales Beobachtungszentrum für Luftschadstoffe (NABEL). To access this data, the REST-API of openweathermap is accessed. As we know that the health insurance is divided into fee regions. Several municipalities belong to these fee regions. For every municipality, we would like to receive the air quality and therefore, we need to first get the WGS84 geocoordinates for the municipality. This can be achieved via the following code:
# %%
lat, lon = get_wgs84_municipality("Wohlen")
print(f"Wohlen coordinates: latitude={lat}, longitude={lon}")
# %%
lat, lon = get_wgs84_municipality("Steinhausen")
print(f"Steinhausen coordinates: latitude={lat}, longitude={lon}")
# %% md
# With these geocoordinates, we can access the openweathermap REST-API. Note, you need to put the API key for the Openweathermap REST-API into your .env file.
# %%
load_dotenv()
API_KEY = os.getenv("APIKeyOpenWeatherMap")

# Replace it with your actual latitude, longitude, and API key
latitude = lat
longitude = lon

api_key = API_KEY

air_quality_data = get_air_quality(latitude, longitude, api_key)

if air_quality_data:
    print(json.dumps(air_quality_data, indent=2))
# %% md
# The NABEL also provides historical data which can be manually downloaded from the website. Unfortunately, the openweathermap API for the historical data is not free of charge. Thus, I decided to go with the manual download.
# In the following, we will have a look at the PM2.5 data.
# %%
df_stations = pd.read_csv(
    os.path.join("data", "nabel", "stations_with_wgs84.csv"), encoding="utf-8"
)


station_name_map = {
    "BASEL-BINNINGEN": "Basel-Binningen",
    "BERN-BOLLWERK": "Bern-Bollwerk",
    "BEROMÜNSTERk": "Beromünster",
    "CHAUMONT": "Chaumont",
    "DAVOS-SEEHORNWALD": "Davos-Seehornwald",
    "DÜBENDORF-EMPA": "Dübendorf-Empa",
    "HÄRKINGEN-A1": "Härkingen-A1",
    "JUNGFRAUJOCH": "Jungfraujoch",
    "LAUSANNE-CÉSAR-ROUX": "Lausanne-César-Roux",
    "LUGANO-UNIVERSITA": "Lugano-Università",
    "MAGADINO-CADENAZZO": "Magadino-Cadenazzo",
    "PAYERNE": "Payerne",
    "RIGI-SEEBODENALP": "Rigi-Seebodenalp",
    "SION-AÉROPORT-A9": "Sion-Aéroport-A9",
    "TÄNIKON": "Tänikon",
    "ZÜRICH-KASERNE": "Zürich-Kaserne",
}


s_Pollutant = [
    "CO",
    "CPC",
    "EC",
    "NMVOC",
    "NO2",
    "NOX",
    "O3",
    "PM2.5",
    "PM10",
    "PREC",
    "RAD",
    "SO2",
    "TEMP",
]
s_Year = list(range(2000, 2026, 1))
new_columns = {}

for Pollutant in s_Pollutant:
    fn_Pollutant = Pollutant + ".csv"

    pth_historical_airquality = os.path.join(
        "data", "nabel", "historical_data", fn_Pollutant
    )
    # First, find out which row starts the real data (the header)
    with open(pth_historical_airquality, encoding="latin-1") as f:
        for i, line in enumerate(f):
            if line.startswith("Datum/Zeit"):
                data_start = i
                break

    # Now, load only the table, skipping metadata rows
    df = pd.read_csv(
        pth_historical_airquality, sep=";", skiprows=data_start, encoding="latin-1"
    )
    # Let us now remove all empty data lines.
    df_clean = df.dropna(how="all", subset=df.columns[1:])
    # df = df_clean
    df["Datum/Zeit"] = pd.to_datetime(
        df["Datum/Zeit"], format="%d.%m.%Y", errors="coerce"
    )

    for Year in s_Year:
        df_Yearly = df[df["Datum/Zeit"].dt.year == Year].copy()
        df_Yearly.loc[:, "Year"] = df_Yearly["Datum/Zeit"].dt.year
        df_Yearly.loc[:, "Month"] = df_Yearly["Datum/Zeit"].dt.month

        # List of station columns (all except 'Datum/Zeit', 'Year', 'Month')
        station_cols = [
            col
            for col in df_Yearly.columns
            if col not in ["Datum/Zeit", "Year", "Month"]
        ]

        # For median per year:
        median_per_year = df_Yearly.groupby(["Year"])[station_cols].median()
        col_name = f"{Pollutant}_{Year}"
        # Prepare a list with the right value for each row (station) in df_stations
        col_vals = []
        for _, row in df_stations.iterrows():
            st_name = row["Station"]
            # Find CSV name for this station
            csv_station = station_name_map[st_name]
            if csv_station in median_per_year:
                col_vals.append(median_per_year[csv_station].values[0])
            else:
                col_vals.append(None)
        new_columns[col_name] = col_vals

# 2. Add all new columns at once
df_newcols = pd.DataFrame(new_columns)
df_result = pd.concat([df_stations, df_newcols], axis=1)

# 3. Save or use
df_result.to_csv(
    os.path.join("data", "nabel", "stations_with_wgs84_with_pollution.csv"),
    index=False,
    encoding="utf-8",
)
# %%
Enriched_Pollution_Per_Station = pd.read_csv(
    os.path.join("data", "nabel", "stations_with_wgs84_with_pollution.csv"),
    encoding="utf-8",
)
Enriched_Pollution_Per_Station.head()
# %% md
# Next, we will use the air pollution data at the stations to interpolate the yearly median air pollution values at a particular municipality based on the Inverse Distance Weighting (IDW) algorithm.
# %%
Year = 2025
Pollutant = "PM2.5"
value_col = Pollutant + "_" + str(Year)
lat, lon = get_wgs84_municipality("Steinhausen")


idw_interpolate(
    stations_df=Enriched_Pollution_Per_Station,
    target_lat=lat,
    target_lon=lon,
    value_col=value_col,
    k=4,
    power=2,
)
# %% md
# Next, we go over all the cantons and all its municipalities and determine the air pollution concentrations per year. So, we then can create a heatmap per year and pollutant which expresses the relation between the pollutant concentration and the health insurance fee.
# %%
Year = 2025
Pollutant = "PM2.5"
vk_Kanton_Pollutant = {}
vk_Pollutant = {}
value_col = Pollutant + "_" + str(Year)
pth_Fees = os.path.join(os.getcwd(), "data", "healthinsurance", "Prämien_CH.csv")
Data = LoadData(pth_Fees)
if Data is not None:
    for Kanton in swiss_cantons_abbr_to_name.keys():
        s_Region = GetRegion(Data, Kanton)
        # if isinstance(s_Region, (list, set)):
        #    s_Region = ', '.join(str(region) for region in s_Region)
        pth_Municipality = os.path.join(
            os.getcwd(), "data", "healthinsurance", "praemienregionen-ab-2025.xlsx"
        )
        if len(s_Region) > 1:
            s_Municipality = GetMunicipalities_MultipleFeeRegions(
                pth_Municipality, Kanton, s_Region[0]
            )
            # Finding the canton and fee region based on the name of the municipality can be achieved by the following command:
            Kanton, Region = GetKantonRegionFromGemeinde(
                pth_Municipality, s_Municipality[0]
            )
            print(
                f"For municipality {s_Municipality[0]}, the canton is {Kanton} and the fee region is {Region}."
            )
        else:
            s_Municipality = GetMunicipalities_PerCanton(
                swiss_cantons_abbr_to_name[Kanton]
            )
        print(
            f"In the fee region in Canton {Kanton}, the municipalities belong to: {s_Municipality}"
        )
        for Municipality in s_Municipality:
            lat, lon = get_wgs84_municipality("Steinhausen")
            Pollutant_Interpolated = idw_interpolate(
                stations_df=Enriched_Pollution_Per_Station,
                target_lat=lat,
                target_lon=lon,
                value_col=value_col,
                k=4,
                power=2,
            )
            vk_Pollutant[Municipality] = Pollutant_Interpolated
        if vk_Pollutant:
            vk_Kanton_Pollutant[Kanton] = statistics.median(vk_Pollutant.values())
        else:
            vk_Kanton_Pollutant[Kanton] = np.nan
        vk_Pollutant = {}
# %%
vk_Kanton_Pollutant
# %%
# Example dataframes (replace with your real data)
df_air = pd.DataFrame(
    {
        "Kanton": list(vk_Kanton_Pollutant.keys()),
        "Airpollution": list(vk_Kanton_Pollutant.values()),
    }
)
df_fee = pd.DataFrame(
    {"Kanton": ["Aargau", "Bern", "Zürich"], "HealthInsuranceFee": [350, 420, 390]}
)

# Merge on "Kanton"
df = pd.merge(df_air, df_fee, on="Kanton")

# %%


fig = px.imshow(
    [df["Airpollution"]],
    labels=dict(x="Kanton", color="Airpollution"),
    x=df["Kanton"],
    y=["Airpollution"],  # Dummy y-label
    color_continuous_scale="YlOrRd",
)

fig.update_layout(title="Air Pollution by Kanton", yaxis=dict(showticklabels=False))
fig.show()
