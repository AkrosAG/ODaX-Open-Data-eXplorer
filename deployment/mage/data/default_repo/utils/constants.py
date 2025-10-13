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

list_tariff = [("TAR-BASE", "Grundversicherung"),
    ("TAR-DIV", "Telmed/Div."),
    ("TAR-HMO", "HMO"),
    ("TAR-HAM", "Hausarztmodell")]


list_age = [("AKL-KIN", "Kinder"),
    ("AKL-JUG", "Jugendliche"),
    ("AKL-ERW", "Erwachsene")]


list_age_subgroup = [
    ("K1", "Einzelkind", "AKL-KIN"),
    ("K3", "1 Geschwister", "AKL-KIN"),
    ("K4", "1 Geschwister", "AKL-KIN"),
    ("K5", "2+ Geschwister", "AKL-KIN"),
    ]
    
list_franchise = [0, 100, 200, 300, 400, 500, 600, 1000, 1500, 2000, 2500]

#Information for different insurers
XLS_INSURERS = '/home/src/raw_data/healthinsurance/BagNr_Mapping_KV.xlsx'
sheets_insurer = ["Zugelassene Krankenversicherer", "zugelassene krankenversicherer"]

#information for different Prämien
CSV_FEES = '/home/src/raw_data/healthinsurance/Prämien_CH.csv'
XLS_MUNIC = '/home/src/raw_data/healthinsurance/praemienregionen-ab-2025.xlsx'