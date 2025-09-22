#!/bin/bash

python3 Postgresql/Data/seed_airpollution_scheme.py
python3 Postgresql/Data/seed_healthinsurance_scheme.py
python3 Superset/scripts/create_superset_dashboard.py