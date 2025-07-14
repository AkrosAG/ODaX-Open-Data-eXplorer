# ODaX-Open-Data-eXplorer

## Installation
1) Clone the repository via git.
2) Checkout the branch ```develop```.
3) Create a virtual environment via python3.1X -m venv venv 
4) Activate it on Windows Powershell via 
   ```source venv\Scripts\activate``` 
   or if you are using a Linux environment on Windows, then
   ```wsl``` and ```source venv/Scripts/activate```
5) Update pip via ```pip install --upgrade pip```
6) Install ```poetry``` in the virtual environment via ```pip install poetry```.
7) Install the dependencies via ```poetry install```.
8) Run the python scripts from the root directory.


In case, wsl is used, open the explorer and go to the directory
```\\wsl$\Ubuntu\home\{USER}``` where you replace ```{USER}``` by your wsl username. Then ensure that in the .ssh folder the same keys and configuration are placed than in your Windows .ssh folder. You may need to copy the content so that you can use the Linux terminal commands to clone the repository.
