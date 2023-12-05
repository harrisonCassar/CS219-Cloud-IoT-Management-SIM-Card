# Cloud-Based IoT Management with SIM Card
The code here was developed as a part of the course project for CS219: Cloud Computing with Professor Songwu Lu. Guidance for the project was graciously provided by Mentor Jinghao Zhao.

## Basic Overview
For our "local" system, we have the following main components:
- Javacard-eSIM applet
- Python modem client (emulates modem that uses the SIM card)

For our "cloud" system, we have the following main components:
- Python UDP server (mediates communication between the Python modem client and the main cloud server)
- Main Python Flask server (manages/accumulates/processes all IoT data for storage and front-end display, as well as expose functionality to perform carrier switches on SIM card)
- Grafana (for data visualization)
- Kafka + Zookeeper (for message passing/data accumulation)

### Downstream Tasks on IoT Data
For this project, we also seek to perform downstream tasks of some kind on the IoT data received from the Modem/SIM client. For now, this downstream task is simply visualization.

When the UDP server (the entry point for the cloud servers) receives data from the Modem/SIM client, it pushes the data to Kafka for consumption by any downstream tasks. In the general "ideal" case for our implementation, this is the only process that the UDP server does.

For our project's data visualization, however, we are utilizing Grafana (v8.2), which has a [semi-working Kafka data source plugin](https://grafana.com/grafana/plugins/hamedkarbasi93-kafka-datasource/) that essentially connects to Kafka, consumes messages from specified topics, and streams that data live for display with Grafana. However, this plugin lacks some critical features that makes the live display not ideal for our purposes, including:
- No support for selection of which data rows (in the Kafka message) to visualize (and which to simply ignore), instead opting for ALL data rows to visualize. This wouldn't work for our purposes, as we desire to have a "timestamp" field in our Kafka messages.
- Only support to have data graphed with timestamp either determined by the message timestamp (when the Kafka message was pushed to Kafka) or when it was consumed from Kafka. This will not work for our purposes, as we desire to have the data graphed at the time that the IoT data was actually collected from the device, which is represented by the "timestamp" field that we've tagged our data with (in the Kafka message itself). In practice, we expect that the message timestamp is no more than a few seconds after the actual data timestamp, however this is fundamentally not ideal.
    
Therefore, if we want to use this plugin, we'd need to upgrade the plugin for our own purposes. This is, reasonably, out of the scope of this project. Therefore, in the meantime, just for a demonstration of functionality, we have the UDP server push to additional special new Kafka topics that are meant JUST FOR THIS PLUGIN'S USE, stripping the "timestamp" field from our Kafka message, and having the plugin just graph with the message timestamp.
    
Additionally, however, we also can avoid Kafka altogether and simply stream data directly to Grafana via [Grafana Live](https://grafana.com/docs/grafana/latest/setup-grafana/set-up-grafana-live/). Grafana v8 introduced Grafana Live, a new streaming capability that allows us to push data to the UI in "near real-time". This is extremely efficient and lightweight (not needing any plugin and/or assisting backend), and can be achieved by simply performing an HTTP POST request to a specific URL in a specific format. For our project purposes, this does not need Kafka, and therefore does not satisfy project requirements. However, we still do this anyway just to demonstrate thefunctionality.

#### Grafana Data Visualization
Here's an example dashboard that we've thrown together for display of this "dummy" setup:

![Grafana Example Dashboard](/docs/grafana_dashboard_example_screenshot.PNG)

### Interfaces and Protocol Message Formats
To ensure the proper integration of these different subsystems, we defined many different interfaces/message formats, which are documented as follows:
- [UDP Protocol Header Definitions - Modem/SIM Client to/from UDP Server](https://docs.google.com/document/d/1mdEs5FQMaLGbHuUZef3QJAGZf7BZ-vpbF44EHkEYv3E/edit?usp=sharing)
- [Kafka Interface Definitioins - UDP Server to/from Main Flask Server](https://docs.google.com/document/d/1W6KI_zLdXfP7h6rauD6cq6sPPcaDoXfJs3fSTZ8QFwk/edit?usp=sharing)

## Setup/Run/Manage in Docker Containers
To perform a full setup/deployment, we utilize `docker compose`. Refer to the following subsections to setup (and then run) our application.

### Setup
Setup is very simple! Simply, install Docker Compose, which can be accomplished by installing Docker Desktop to your machine. See the following article for the download and/or other options for installing Docker Compose: https://docs.docker.com/compose/install/.

For Windows, for Docker, there is a known(?) bug that seemingly causes a memory leak, eating up your computer's memory even if you're not running anything (see https://github.com/docker/for-win/issues/12944). This was experienced by @harrisonCassar when running Docker Desktop 4.20.0 on Windows 10. This may be fixed by upgrading to Docker Desktop 4.25+ (see the issue linked previously). If it becomes annoying/hindering enough, we can temporarily solve this until Docker and/or Windows fixes this issue by placing a memory limit on WSL as follows:

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
- Grafana: 3000
- UDP Server: 6001
- Modem Client: 6002 (locally hosted, not in Docker container)

## Cloud SSH Steps
- Acquire key in file "cs219-instance-2.pem" (keep in root directory and DO NOT COMMIT)
- Run below commands.
`chmod 400 cs219-instance-2.pem`
`ssh -i "cs219-instance-2.pem" ubuntu@ec2-34-211-7-98.us-west-2.compute.amazonaws.com`
