# Cloud-Based IoT Management with SIM Card
The code here was developed as a part of the course project for CS219: Cloud Computing with Professor Songwu Lu. Guidance for the project was graciously provided by Mentor Jinghao Zhao.

## Basic Overview
For our "local" system, we have the following main components:
- Javacard-eSIM applet
- Python modem client (emulates modem that uses the SIM card)

For our "cloud" system, we have the following main components:
- Python UDP server (mediates communication between the Python modem client and the main cloud server)
- Main Python Flask server (manages/accumulates/processes all IoT data for storage and front-end display, as well as expose functionality to perform carrier switches on SIM card)

## Setup/Run/Manage in Docker Containers
To perform a full setup/deployment, we utilize `docker compose`. Refer to the following subsections to setup (and then run) our application.

### Setup
Setup is very simple! Simply, install Docker Compose, which can be accomplished by installing Docker Desktop to your machine. See the following article for the download and/or other options for installing Docker Compose: https://docs.docker.com/compose/install/.

For Windows, for Docker, there is a known(?) bug that seemingly causes a memory leak, eating up your computer's memory even if you're not running anything (see https://github.com/docker/for-win/issues/12944). If it becomes annoying/hindering enough, we can temporarily solve this until Docker and/or Windows fixes this issue by placing a memory limit on WSL as follows:

1. Shutdown WSL:
```bash
wsl --shutdown
```

2. Modify/Create a WSL config file with the following data (assumes you're using WSL2):
```
[wsl2]
memory=2GB
```
**NOTE**: Feel free to up this memory amount if so desired.

3. Restart Docker Desktop
Confirm that your memory usage by the `vmmmem` service (represents all memory used by WSL and your virtual machines) is remaining below the limit you specified (using Task Manager, or a similar monitoring application).

### Run/Manage
To run the suite, we use `docker compose up`:
```bash
# Compose (build and run) all of the Docker Containers
# -d: OPTIONAL, can be used to run in the background.
# --build: can be omitted if you do not need to re-build any of the Docker images (no code changes).
`sudo docker compose up --build`
```

**NOTE**: We recommend having Docker Desktop open to be able to easily view the currently running containers and/or their logs/statuses. However, there exists a number of individual commands to manage the running containers from the command-line (see https://docs.docker.com/engine/reference/commandline/docker/). For an example of these individual commands, see the associated `README.md` files for each of the Docker container sources located throughout this code base (for example, for the Main Python Flask server, refer to `flask-app\README.md`).

## Setup/Run/Manage locally without Docker Container
**NOTE: THIS METHOD OF DEVELOPMENT, TESTING, AND DEPLOYMENT HAS BEEN DEPRECATED! Please instead refer to the above section for steps on how to setup/run/manage the application in Docker containers.**
To setup the local deployment, each subsystem involves a slightly different means/set of dependencies. To run the individual code, follow the setup/run instructions in the READMEs found within the various subdirectories. For example, for the Main Python Flask server, refer to `flask-app\README.md`.

## Port Assignment
- Flask Server: 8000
- Zookeeper: 2181
- Kafka: 29092 (Docker containers), 9092 (host), 9101
- Grafana: 3000 (**NOTE**: currently un-integrated due to some issues with streaming data to it)
- UDP Server: 6001
- Modem Client: 6002