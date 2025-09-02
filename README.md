# ODaX-Open-Data-eXplorer (ODaX)
ODaX is an open-source data analytics platform designed for the analysis of open data.
It serves as a tool to demonstrate to clients the added value of data and how easily and efficiently valuable insights can be extracted from it.

## Installation of the environment wsl on Windows
### wsl installation
Install ```wsl``` (with the Ubuntu distribution) on your Windows dev machine or use Ubuntu instead. Make sure that you do a restart after you installed ```wsl```.

### ssh-key setup
1) To generate an ssh-key use ```ssh-keygen -t ecdsa``` in the .ssh folder of your Windows user account, e.g., ```C:\Users\{USER}\.ssh``` .
2) Then open the Windows explorer and type ```\\wsl.localhost\Ubuntu\home\{USER}``` in the explorer. If there is not already a folder ```.ssh```, create one. Then copy the generated ssh keys from ```C:\Users\{USER}\.ssh``` to the ```.ssh``` folder in the wsl file system. 
3) Please add your public ssh key to your GitHub account.

### Installation of Pycharm
1) Install pycharm and run it as admin.
2) As you have previously installed wsl and restarted the computer, there should be an Ubuntu terminal based on wsl available in your Pycharm. If so, please open this terminal. If not, please check your wsl installation.
3) You can check with ```pwd``` if the selected directory in your Ubuntu terminal session is ```/home/{USER}```. If not, navigate there and perform the following steps.

## Installation of ODaX
1) Clone the repository https://github.com/AkrosAG/ODaX-Open-Data-eXplorer via git in the wsl filesystem, e.g., under ```/home/{USER}```.
2) Checkout the branch ```develop```.
3) Delete the folder ```.vitualenvs``` in ```/home/{USER}``` if it exists.
4) Navigate to the root directory of your project ```/home/{USER}/ODaX-Open-Data-eXplorer```.
5) Create a virtual environment via ```python3.11 -m venv venv```. At the moment, apache superset requries python 3.11.
6) If step 4 does not work, you may need to install the venv extension for your python, i.e., by ```sudo apt install python3.X-venv```. After the installation, try again to create a virtual environment.
7) Using ```wsl```, activate the virtual environment by ```source venv/bin/activate```.
8) Update pip via ```pip install --upgrade pip```
9) Install ```poetry``` in the virtual environment via ```pip install poetry```.
10) Install the dependencies via ```poetry install --no-root```.
11) Go to the Pycharm ```Settings```, then the ```Project: ODaX-Open-Data-eXplorer```, and then the ```Project Interpreter```.
12) Click on ```Add interpreter``` and select ```On WSL```.
13) Add an ```existing``` python interpreter and select the python in the previously created venv ```/home/{USER}/ODaX-Open-Data-eXplorer/venv/bin/python3.X```.
14) Run the python scripts from the root directory in the terminal or use the Pycharm ```Run```/```Debug``` functionality. Remember to set the ```Working directory``` in the ```Run/ Debug configuration``` to the project root directory.
15) Side note: If you want to run a Python file as a Jupyter Notebook, you can right-click on the file and select ```Convert to Jupyter Notebook```.

### Installation of podman
In WSL, the linux distribution Ubuntu is emulated. Please follow the installation steps for Ubuntu documented at https://podman.io/docs/installation. Mainly, ```sudo apt -y install podman``` needs to be executed.

### Installation of superset
For using superset, several Linux packages need to be added. Please follow the installation steps documented at https://superset.apache.org/docs/installation/pypi for the Ubuntu 24.04 LTS distribution.

### Installation of postgresql
Please follow the installation steps documented at https://www.postgresql.org/download/linux/ubuntu/ to install postgresql in your distribution packages.
Mainly, the command ```sudo apt install postgresql``` that needs to be executed.

### Installation of the superset connector to postgresql
``` sudo apt install libpq-dev```
```poetry add psycopg2```

## .env file
Please make sure to get an API key from the website https://home.openweathermap.org/ for receiving the current air quality data via a REST API. Optionally, if you want to use the AirIQ air quality data, you can request an API key from  https://www.iqair.com/ . 
Create an .env file in the project root and add the API keys as values of the following variables:
```
APIKeyOpenWeatherMap = ""
APIKeyAirIQ = ''
```
## Further information
Due to an error when using superset which was based on a bug in the marshmellow package 4.0.0, we have downgraded the marshmellow package to the previous version. This may get obsolete in the future.


# Deployment
In case, the execution of a bash script fails, please execute the following command:
```sudo apt install dos2unix``` and next ```dos2unix BASH-Script.sh```. It ensures, that the line endings are correct and an execution on a Linux system is possible. 

# Architecture

ODaX follows a modular architecture designed for flexibility and extensibility in data analysis workflows. The architecture consists of the following key components:

1. **Data Import Layer**: Specialized modules in the `imping` package handle importing data from various sources, including CSV files, Excel files, and external APIs. Each data source has its own dedicated module with specific functions for data retrieval and initial processing.

2. **Data Processing Layer**: Once imported, data is processed using pandas DataFrames for manipulation, transformation, and analysis. This layer includes functions for coordinate transformations, data interpolation, and statistical calculations.

3. **Analysis Layer**: This layer combines data from different sources to extract insights. It includes functions for correlating data (e.g., air quality with health insurance fees) and performing statistical analyses.

4. **Visualization Layer**: The project uses Apache Superset for creating interactive visualizations and dashboards to present the analysis results.

5. **Notebook Interface**: Jupyter notebooks provide an interactive environment for data exploration and analysis, allowing users to combine code, visualizations, and documentation.

The architecture is designed to be modular, allowing new data sources to be added easily by creating new modules in the `imping` package.

# Modules

ODaX is organized into the following main modules:

## Data Modules

### `data/`
Contains raw and processed data files used by the application:
- `healthinsurance/`: Health insurance data from the Swiss Federal Office of Public Health (BAG)
- `nabel/`: Air quality data from the National Air Pollution Monitoring Network (NABEL)

## Import Processing Modules (`imping/`)

### `imping/healthinsurance/`
Modules for importing and processing health insurance data:
- `lib_healthinsurance.py`: Functions for loading health insurance data, retrieving fee information, and mapping municipalities to fee regions

### `imping/meteoswiss/`
Modules for importing and processing meteorological data from MeteoSwiss:
- `getStations.py`: Functions for retrieving station information from MeteoSwiss

### `imping/nabel_airquality/`
Modules for importing and processing air quality data:
- `lib_openweathermap.py`: Functions for retrieving current air quality data from the OpenWeatherMap API
- `lib_geocoordinates.py`: Functions for coordinate transformations (Swiss LV95 to WGS84) and spatial interpolation of air quality data

## Analysis Scripts

### Root-level Python Scripts
- `run_openweathermap.py`: Script for fetching air quality data from OpenWeatherMap API
- `run_GeocoordinateTransformation.py`: Script for transforming Swiss coordinates to WGS84
- `airquality_healthinsurancefees.py`: Comprehensive analysis script that combines air quality and health insurance data

## Notebook Interfaces

### Jupyter Notebooks
- `airquality_healthinsurancefees.ipynb`: Interactive notebook version of the analysis script for exploring the relationship between air quality and health insurance fees




# Postgres and Superset Integration for Health Insurance Data

This repository includes scripts to load the Swiss health insurance premiums into PostgreSQL so the data can be explored in Apache Superset.

Prerequisites
- WSL Ubuntu or Ubuntu shell
- podman (or use your own PostgreSQL), and psql client installed
- A PostgreSQL password stored as a Podman secret named pg_password (see below)

1) Start a local PostgreSQL with Podman
- Create the secret (once):
  echo "yourStrongPassword" | podman secret create pg_password -
- Start the container:
  ./infrastructure/local/setup_odax_pg.sh

This starts postgres:15 on localhost:5432 with:
- DB: odax
- User: odax
- Password: provided via secret pg_password

2) Load health insurance premiums into PostgreSQL
- Export PGPASSWORD for psql to authenticate:
  export PGPASSWORD=yourStrongPassword
- Run the loader script:
  ./infrastructure/local/load_healthinsurance_to_pg.sh

The script will:
- Create schema odax and table odax.healthinsurance_premiums if they do not exist
- Load data from data/healthinsurance/Prämien_CH.csv (semicolon-separated, Latin-1 encoding)
- Create a view odax.v_healthinsurance_premiums with clean column names

3) Connect Apache Superset to the database
- In Superset, add a database connection with:
  postgresql+psycopg2://odax:yourStrongPassword@host.docker.internal:5432/odax
  Note: If Superset runs in Docker on Windows, use host.docker.internal to reach Postgres exposed on the host.
- Explore the dataset by adding the table or view:
  odax.v_healthinsurance_premiums (recommended)
  or
  odax.healthinsurance_premiums

Column reference (v_healthinsurance_premiums)
- insurer_bag_code (text)
- canton (text)
- territory (text)
- business_year (int)
- survey_year (int)
- fee_region (text)
- age_class (text)
- accident_coverage (text)
- tariff_code (text)
- tariff_type (text)
- sub_age_group (text)
- franchise_level_code (text)
- franchise_label (text)
- premium_chf (numeric)
- is_base_p (boolean)
- is_base_f (boolean)
- tariff_label (text)

Troubleshooting
- psql: could not connect to server: Ensure the container is running: podman ps
- Authentication failure: Make sure PGPASSWORD is exported and matches the pg_password secret used for the container.
- Encoding issues: The loader enforces LATIN1 client encoding to correctly load the German characters present in the CSV header and data.


# Poetry environment setup (quickstart)

You can use Poetry to manage the virtual environment and dependencies for this project (Python 3.11 is required due to Superset):

Recommended (Poetry manages the venv):
- Ensure Python 3.11 is installed in WSL/Ubuntu.
- Install Poetry (one-time): pipx install poetry or pip install --user poetry
- Tell Poetry to use Python 3.11: poetry env use 3.11
- Install dependencies (including dev tools): poetry install --with dev
- Activate the environment: poetry shell

Alternative (aligns with steps above in README):
- Create venv manually: python3.11 -m venv venv
- Activate: source venv/bin/activate
- Install Poetry into that venv: pip install poetry
- Install dependencies into the active venv: poetry install --no-root --with dev

Notes
- IDE: In PyCharm, set the interpreter to the Poetry venv (poetry env info --path) or to venv/bin/python if you created it manually.
- Dev dependencies: pytest and flake8 are installed only if you include the dev group (use --with dev). For a slimmer runtime-only env, omit --with dev.
- Common checks: poetry check (validates pyproject), poetry lock (updates lockfile), poetry run pytest (runs tests).

