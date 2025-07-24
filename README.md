# ODaX-Open-Data-eXplorer (ODaX)
ODaX is an open-source data analytics platform designed for the analysis of open data.
It serves as a tool to demonstrate to clients the added value of data and how easily and efficiently valuable insights can be extracted from it.

## Installation of the environment wsl on Windows
### wsl installation
Install ```wsl``` (with the Ubuntu distribution) on your Windows dev machine or use Ubuntu instead. Make sure that you do a restart after you installed ```wsl```.

### ssh-key setup
1) To generate an ssh-key use ```ssh-keygen -t ecdsa``` in the .ssh folder of your Windows user account, e.g., ```C:\Users\{USER}\.ssh``` .
2) Then open the Windows explorer and type ```\\wsl$\Ubuntu\home\{USER}``` in the explorer. If there is not already a folder ```.ssh```, create one. Then copy the generated ssh keys from ```C:\Users\{USER}\.ssh``` to the ```.ssh``` folder in the wsl file system. 
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
5) Create a virtual environment via python3.1X -m venv venv
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

## .env file
Please make sure to get an API key from the website https://home.openweathermap.org/ for receiving the current air quality data via a REST API. Optionally, if you want to use the AirIQ air quality data, you can request an API key from  https://www.iqair.com/ . 
Create an .env file in the project root and add the API keys as values of the following variables:
```
APIKeyOpenWeatherMap = ""
APIKeyAirIQ = ''
```


# Architecture

ODaX follows a modular architecture designed for flexibility and extensibility in data analysis workflows. The architecture consists of the following key components:

1. **Data Import Layer**: Specialized modules in the `imping` package handle importing data from various sources, including CSV files, Excel files, and external APIs. Each data source has its own dedicated module with specific functions for data retrieval and initial processing.

2. **Data Processing Layer**: Once imported, data is processed using pandas DataFrames for manipulation, transformation, and analysis. This layer includes functions for coordinate transformations, data interpolation, and statistical calculations.

3. **Analysis Layer**: This layer combines data from different sources to extract insights. It includes functions for correlating data (e.g., air quality with health insurance fees) and performing statistical analyses.

4. **Visualization Layer**: The project uses Plotly and Dash for creating interactive visualizations and dashboards to present the analysis results.

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

