# ODaX-Open-Data-eXplorer

## Installation
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

## Installation
1) Clone the repository https://github.com/AkrosAG/ODaX-Open-Data-eXplorer via git in the wsl filesystem, e.g., under ```/home/{USER}```.
2) Checkout the branch ```develop```.
3) Delete the folder ```.vitualenvs``` in ```/home/{USER}``` if it exists.
4) Navigate to the root directory of your project ```/home/{USER}/ODaX-Open-Data-eXplorer```.
4) Create a virtual environment via python3.1X -m venv venv
5) If step 4 does not work, you may need to install the venv extension for your python, i.e., by ```sudo apt install python3.X-venv```. After the installation, try again to create a virtual environment.
6) Using ```wsl```, activate the virtual environment by ```source venv/bin/activate```.
7) Update pip via ```pip install --upgrade pip```
8) Install ```poetry``` in the virtual environment via ```pip install poetry```.
9) Install the dependencies via ```poetry install --no-root```.
10) Go to the Pycharm ```Settings```, then the ```Project: ODaX-Open-Data-eXplorer```, and then the ```Project Interpreter```.
11) Click on ```Add interpreter``` and select ```On WSL```.
11) Add an ```existing``` python interpreter and select the python in the previously created venv ```/home/{USER}/ODaX-Open-Data-eXplorer/venv/bin/python3.X```.
12) Run the python scripts from the root directory in the terminal or use the Pycharm ```Run```/```Debug``` functionality. Remember to set the ```Working directory``` in the ```Run/ Debug configuration``` to the project root directory.

## .env file
Please make sure to get an API key from the website https://home.openweathermap.org/ for receiving the current air quality data via a REST API. Optional, if you want to use the AirIQ air quality data, you can request an API key from  https://www.iqair.com/ . 
Create an .env file in the project root and add the API keys as values of the following variables:
```
APIKeyOpenWeatherMap = ""
APIKeyAirIQ = ''
```



