# Main Python Flask Server
This directory contains all of the code for the main cloud-based Flask server.

## Setup
Follow the below steps to setup (and run) the server.

### Activate a Virtual Environment
If you haven't created a virtual environment for this app yet, first make one by running the following command (assuming Python3 is installed on your machine already):
```bash
# Create a new virtual environment (if you haven't already).
python3 -m venv /path/to/new/virtual/environment
```

Then, we need to activate it by running the following commands:
```bash
# Activate the virtual environment.
# on POSIX:
source <venv>/bin/activate # bash/zsh
<venv>/bin/Activate.ps1 # Powershell
# on Windows:
<venv>\Scripts\activate.bat # cmd.exe
<venv>\Scripts\Activate.ps1 # Powershell
```

For more information on creation/activation, refer to the Python `venv` module documentation: https://docs.python.org/3/library/venv.html#how-venvs-work.

### Install Dependencies
This only needs to be done once! If you've already done this before, then you may skip this step.

We can install all of the dependencies for our Flask server automatically with one command...
```bash
pip install -r flask-app/requirements.txt
```

...or manually:
```bash
pip install Flask
pip install Flask-WTF
pip install Flask-Bootstrap
```

### Start the Flask Server
We start the Flask app via the following commands:
```bash
# Change into the Flask app's directory.
cd flask-app

# Run the Flask app.
flask run
```