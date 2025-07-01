#%%
import pandas as pd
import numpy as np
import os
from imping.healthinsurance.lib_healthinsurance import LoadData, GetFeesByParameters, GetKVNameFromBAGNumber, GetAlterunterGruppenProVersicherer, GetRegion, GetKantonRegionFromGemeinde
from imping.nabel_airquality.openweathermap import get_air_quality
#%%
from imping.healthinsurance.lib_healthinsurance import GetMunicipalities
#%% md
#  # Analysis of the health insurance data
#%% md
#  ## Insurances in Switzerland
#  First, we outline the health insurance data from the Bundesamt für Gesundheit (BAG) published over opendataswiss.
#%%
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
        "ZH": "Zürich"
    }
#%% md
# First, we need to load the data.
#%%
# Path to the file containing the health insurance data
pth_Fees = os.path.join(os.getcwd(), 'data', 'healthinsurance', 'Prämien_CH.csv')
Data = LoadData(pth_Fees)
#%% md
# To get an overview of which fee regions for health insurances exist in Switzerland, please run the following cell:
#%%
if Data is not None:
    for Kanton in swiss_cantons_abbr_to_name.keys():
        s_Region = GetRegion(Data, Kanton)
        if isinstance(s_Region, (list, set)):
            s_Region = ', '.join(str(region) for region in s_Region)
        print(f"Kanton {Kanton} has the regions: {s_Region}")
#%% md
# The following code outputs which municipalities belong to the fee region PR-REG CH0 of the canton Bern (BE). If you are interested in another fee region or canton, feel free to adjust the sample code. Knowing which municipality is in a fee region enables to detect the extrapolated air pollution as demonstrated later on in this notebook.
#%%
if Data is not None:
    s_Region = GetRegion(Data, 'BE')
    pth_Municipality = os.path.join(os.getcwd(), 'data', 'healthinsurance', 'praemienregionen-ab-2025.xlsx')
    s_Municipality = GetMunicipalities(pth_Municipality, 'BE', s_Region[0])
    print(f"In the fee region in Canton BE, the municipalities belong to: {s_Municipality}")
    # Finding the canton and fee region based on the name of the municipality can be achieved by the following command:
    Kanton, Region = GetKantonRegionFromGemeinde(pth_Municipality, s_Municipality[0])
    print(f"For municipality {s_Municipality[0]}, the canton is {Kanton} and the fee region is {Region}.")

#%% md
# In Switzerland, there are three age groups, i.e., the group for children AKL-KIN, the group for young adults AKL-JUG, and the group for adults over 25 years AKL-ERW.
#%%
s_Altersklasse = ['AKL-KIN', 'AKL-JUG', 'AKL-ERW']
#%% md
# Further, when being employed in Switzerland, the employer provides the accident insurance. To avoid being insured twice, the accident insurance can be excluded from the health insurance model.
#%%
s_Unfalldeckung = ['MIT-UNF', 'OHN-UNF']
#%% md
# The third option to customize the health insurance model is the franchise. For each age group, there are several franchise options available.
#%%
vk_Franchise = {
    'AKL-KIN': ['FRA-0', 'FRA-100','FRA-200', 'FRA-300', 'FRA-400', 'FRA-500', 'FRA-600'],
    'AKL-JUG': ['FRA-300', 'FRA-500', 'FRA-1000', 'FRA-1500', 'FRA-2000', 'FRA-2500'],
    'AKL_ERW': ['FRA-0', 'FRA-100','FRA-200', 'FRA-300', 'FRA-400', 'FRA-500', 'FRA-600', 'FRA-1000', 'FRA-1500', 'FRA-2000', 'FRA-2500']
}
#%% md
# Moreover, there is a model called "Hausarztmodel" (TAR-HAM), which requires consulting a particular general practitioner before further treatment. Another model requires visiting a health maintainance organization (TAR-HMO) before further treatment is possible. The TAR-BASE is the "Grundversicherung" and allows to choose the physician freely. The model TAR-DIV requires a telemedical consultations before any further treatment.
#%%
s_Tariftyp = ['TAR-BASE', 'TAR-DIV', 'TAR-HMO', 'TAR-HAM']
#%% md
# When considering the health insurance for children, there are even different subgroups available depending on the number of siblings a child has. To receive this information for all insurance companies and a certain canton and fee region, the following command can be used:
#%%
vk_Altersuntergruppe = GetAlterunterGruppenProVersicherer(Data, Kanton = Kanton, Region = 'PR-REG CH'+Region, Altersklasse=s_Altersklasse[0], Unfalldeckung=s_Unfalldeckung[0], Franchise = vk_Franchise[s_Altersklasse[0]][0], Tariftyp = s_Tariftyp[0])
if vk_Altersuntergruppe:
    print("Altersuntergruppen per Versicherer for your selection:")
    for versicherer, altersgruppen in vk_Altersuntergruppe.items():
        print(f"- Versicherer {versicherer}: Altersuntergruppen {altersgruppen}")
else:
    print("No Altersuntergruppen found for the selected criteria.")
#%% md
# Note, that the K1 model is for only children, the model with the highest number is for children with at least two siblings. If there is another model with a number in between K1 and the highest model, it is for children with one sibling. So, for the insurance company with BAG number 1542, the K1 model is for only children, the K4 for children with one sibling, and the K5 model for chlidren with at least two siblings.
#%% md
# The BAG number is a unique number, the Bundesamt für Gesundheit uses to identify an insurance company. To receive the name of the insurance company in Gemran, French, and Italian based on this number, the following code can be used:
#%%
pth_BAGMapping = os.path.join(os.getcwd(), 'data', 'healthinsurance', 'BagNr_Mapping_KV.xlsx')
BAG_Number = 8
Name_HealthinInsurance = GetKVNameFromBAGNumber(8, pth_BAGMapping)
print(f"The insurer for BAG number {BAG_Number} is: {Name_HealthinInsurance}")

#%% md
# If you are interested in determining the health insurance fees for a certain insurance model, then execute the following code, which returns you all insurance fees of all insurance companies whose insurances fit your specifications:
#%%
AltersGruppe = vk_Altersuntergruppe[BAG_Number][0]
Fees = GetFeesByParameters(Data = Data, Kanton = Kanton, Region = 'PR-REG CH'+Region, Altersklasse=s_Altersklasse[0], Unfalldeckung=s_Unfalldeckung[0], Franchise = vk_Franchise[s_Altersklasse[0]][0], Tariftyp = s_Tariftyp[0], Altersgruppe=AltersGruppe)
print(Fees)
#%% md
# To receive the specific fee for a certain insurance company, then filter the fees by the BAG number as following:
#%%
FeePerInsurance = Fees[Fees['Versicherer']==BAG_Number]
print(FeePerInsurance)
#%% md
# ## Analysis of the air quality data
#%% md
# 
#%%

#%%
