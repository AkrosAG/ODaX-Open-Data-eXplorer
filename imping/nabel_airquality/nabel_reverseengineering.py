import requests
import datetime

# Define your time window
today = datetime.date.today()
start_date = today - datetime.timedelta(days=30)

# BAFU endpoint (unofficial)
url = "https://nabelapi.apps.bafu.admin.ch/v1/query"

# Payload: adjust for other pollutants or stations
payload = {
    "stations": ["ZUE"],  # Zürich-Kaserne
    "components": ["NO2"],  # NO2
    "dateFrom": start_date.isoformat(),
    "dateTo": today.isoformat(),
    "resolution": "hour",
    "format": "csv"
}

# Headers
headers = {
    "Content-Type": "application/json",
}

# Send the POST request
response = requests.post(url, json=payload, headers=headers)

# Save CSV
if response.ok:
    with open(f"nabel_no2_zue_{today}.csv", "wb") as f:
        f.write(response.content)
    print("Download successful!")
else:
    print("Failed:", response.status_code, response.text)
