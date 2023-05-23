# Main Python Flask Server
This directory contains all of the code for the main cloud-based Flask server.

## Setup/Run/Manage in Docker Container
Follow the below steps to setup, run, and manage the server in a Docker container.

```bash
# Download and install Docker.
# See the documentation: https://docs.docker.com/get-docker/.

# Open Docker Desktop

# Check you've successfully installed docker.
`docker --help`

# Build image (only needs to be done after modifying installed dependencies and/or OS-level package versions).
`cd /` # root directory, so that Docker's context is at the top-level to allow copying of the `common` directory.
`docker image build -t flask_server -f flask_server/Dockerfile .` # -t: Name to be given to built image

# Run the container (if container does not exist yet and/or image is different)
`docker run --name flask_server -p 8000\:8000 flask_server` # specify option -d to run in detached mode

# To start/stop/restart a docker container with our image:
`docker restart flask_server`
`docker stop flask_server`
`docker start flask_server`

# To remove a container:
`docker rm flask_server` # use the --force option to remove running containers

# To remove all stopped containers:
`docker container prune`

# To view all available Docker images:
`docker image list`

# To view all running Docker containers:
`docker ps`

# To view IP address for running Docker container:
`docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' flask_server`
```

## Setup/Run/Manage locally without Docker Container
**NOTE: THIS METHOD OF DEVELOPMENT, TESTING, AND DEPLOYMENT HAS BEEN DEPRECATED! Please instead refer to the above section for steps on how to setup/run/manage the application in a Docker container.**

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

We can install all of the Python dependencies for our Flask server automatically with one command...
```bash
pip install -r flask-app/requirements.txt
```

...or manually:
```bash
pip install Flask
pip install Flask-WTF
pip install Flask-Bootstrap
pip install kafka-python
```

Additionally, we have to install Apache Kafka and Apache Zookeeper to allow us to use Kafka. For Windows, follow the steps outlined here: https://shaaslam.medium.com/installing-apache-kafka-on-windows-495f6f2fd3c8.

### Start the Flask Server
We start the Flask app via the following commands:
```bash
# Change into the Flask app's directory.
cd flask-app

# Run the Flask app.
flask run
```