# Cloud-Based IoT Management with SIM Card
The code here was developed as a part of the course project for CS219: Cloud Computing with Professor Songwu Lu, and extended as a part of Harrison Cassar's Masters capstone project. Guidance for the course project was graciously provided by Mentor Jinghao Zhao, and guidance for the capstone project was graciously provided by Mentor Boyan Ding.

- [Cloud-Based IoT Management with SIM Card](#cloud-based-iot-management-with-sim-card)
  - [Basic Overview](#basic-overview)
    - [Downstream Tasks on IoT Data](#downstream-tasks-on-iot-data)
      - [Grafana Data Visualization](#grafana-data-visualization)
    - [Interfaces and Protocol Message Formats](#interfaces-and-protocol-message-formats)
  - [To Setup](#to-setup)
    - [Local Subsystem](#local-subsystem)
      - [WSL](#wsl)
      - [Smart Card Reader](#smart-card-reader)
      - [Mocked SIM card](#mocked-sim-card)
      - [srsRAN](#srsran)
    - [Cloud Subsystem](#cloud-subsystem)
      - [Without Docker (Locally/Natively)](#without-docker-locallynatively)
      - [Quirks](#quirks)
        - [Kafka Topic Non-Existent on Startup](#kafka-topic-non-existent-on-startup)
        - [Startup Order Affecting Downstream Messages](#startup-order-affecting-downstream-messages)
        - [Docker for Windows Memory Leak](#docker-for-windows-memory-leak)
  - [To Run](#to-run)
    - [Local Subsystem](#local-subsystem-1)
      - [Smart Card Reader Service](#smart-card-reader-service)
      - [Modified srsRAN Components](#modified-srsran-components)
      - [Local Python Proxy Applications](#local-python-proxy-applications)
    - [Cloud Subsystem](#cloud-subsystem-1)
  - [Port Assignment](#port-assignment)
  - [Cloud SSH Steps](#cloud-ssh-steps)

## Basic Overview
For our "local" system, we have the following main components:
- Mocked SIM card with a Java Card, loaded with an [eSIM applet](https://github.com/JinghaoZhao/eSIM-Applet-dev)
- [srsRAN 4G SDR implementation, modified with custom modem client logic for this application](https://github.com/harrisonCassar/srsRAN_4G_CloudIoTManagement/tree/cloudiotmanagement) (previously the [Python modem client](https://github.com/harrisonCassar/CS219-Cloud-IoT-Management-SIM-Card/tree/srsran-extension/modem), which emulated the modem that uses the SIM card)
- Two instances of a [Python proxy application](https://github.com/harrisonCassar/CS219-Cloud-IoT-Management-SIM-Card/tree/srsran-extension/proxy), one running in native Windows, and the other in WSL (this is a workaround needed due to issues with downlinking UDP traffic from Docker into WSL2 in Windows 11).

For our "cloud" system, we have the following main components:
- [Python UDP server](https://github.com/harrisonCassar/CS219-Cloud-IoT-Management-SIM-Card/tree/srsran-extension/udp_server) (mediates communication between the local subsystem and the rest of the cloud subsystem)
- [Main Python Flask server](https://github.com/harrisonCassar/CS219-Cloud-IoT-Management-SIM-Card/tree/srsran-extension/flask_server) (manages/accumulates/processes all IoT data for storage and front-end display, as well as expose functionality to perform carrier switches on SIM card)
- [Grafana](https://github.com/harrisonCassar/CS219-Cloud-IoT-Management-SIM-Card/tree/srsran-extension/grafana) (for data visualization)
- [Kafka](https://docs.confluent.io/kafka/overview.html) + [Zookeeper](https://docs.confluent.io/platform/current/kafka-metadata/zk-production.html) (for message passing/data accumulation)

### Downstream Tasks on IoT Data
For this project, we also seek to perform downstream tasks of some kind on the IoT data received from the Modem/SIM client. For now, this downstream task is simply visualization.

When the UDP server (the entry point for the cloud servers) receives data from the local Modem/SIM client, it pushes the data to Kafka for consumption by any downstream tasks. In the general "ideal" case for our implementation, this is the only process that the UDP server does.

For our project's data visualization, however, we are utilizing Grafana (v8.2), which has a [semi-working Kafka data source plugin](https://grafana.com/grafana/plugins/hamedkarbasi93-kafka-datasource/) that essentially connects to Kafka, consumes messages from specified topics, and streams that data live for display with Grafana. However, this plugin lacks some critical features that makes the live display not ideal for our purposes, including:
- No support for selection of which data rows (in the Kafka message) to visualize (and which to simply ignore), instead opting for ALL data rows to visualize. This wouldn't work for our purposes, as we desire to have a "timestamp" field in our Kafka messages.
- Only support to have data graphed with timestamp either determined by the message timestamp (when the Kafka message was pushed to Kafka) or when it was consumed from Kafka. This will not work for our purposes, as we desire to have the data graphed at the time that the IoT data was actually collected from the device, which is represented by the "timestamp" field that we've tagged our data with (in the Kafka message itself). In practice, we expect that the message timestamp is no more than a few seconds after the actual data timestamp, however this is fundamentally not ideal.
    
Therefore, if we want to use this plugin, we'd need to upgrade the plugin for our own purposes. This is, reasonably, out of the scope of the original project and its first extension. Therefore, in the meantime, just for a demonstration of functionality, we have the UDP server push to additional special new Kafka topics that are meant JUST FOR THIS PLUGIN'S USE, stripping the "timestamp" field from our Kafka message, and having the plugin just graph with the message timestamp.
    
Additionally, however, we also can avoid Kafka altogether and simply stream data directly to Grafana via [Grafana Live](https://grafana.com/docs/grafana/latest/setup-grafana/set-up-grafana-live/). Grafana v8 introduced Grafana Live, a new streaming capability that allows us to push data to the UI in "near real-time". This is extremely efficient and lightweight (not needing any plugin and/or assisting backend), and can be achieved by simply performing an HTTP POST request to a specific URL in a specific format. For our project purposes, this does not need Kafka, and therefore does not satisfy project requirements. However, we still do this anyway just to demonstrate the functionality.

#### Grafana Data Visualization
Here's an example dashboard that we've thrown together for display of this "dummy" setup:

![Grafana Example Dashboard](/docs/grafana_dashboard_example_screenshot.PNG)

### Interfaces and Protocol Message Formats
To ensure the proper integration of these different subsystems, we defined many different interfaces/message formats, which are documented as follows:
- [UDP Protocol Header Definitions - Modem/SIM Client to/from UDP Server](https://docs.google.com/document/d/1mdEs5FQMaLGbHuUZef3QJAGZf7BZ-vpbF44EHkEYv3E/edit?usp=sharing)
- [Kafka Interface Definitioins - UDP Server to/from Main Flask Server](https://docs.google.com/document/d/1W6KI_zLdXfP7h6rauD6cq6sPPcaDoXfJs3fSTZ8QFwk/edit?usp=sharing)

## To Setup
### Local Subsystem
#### WSL
Due to our local subsystem's usage of a [modified fork of srsRAN](https://github.com/harrisonCassar/srsRAN_4G_CloudIoTManagement/tree/cloudiotmanagement) to represent a (software) mobile network infrastructure, which runs in a Linux environment only, WSL must be installed. Although WSL can be installed on Windows 10, many other setup steps are more stable and greatly simplified through the usage of Windows 11. Due to our local subsystem's usage of a physical Java Card being read by a smart card reader connected via USB to our Windows machine (see Figure \ref{fig:smart-card-reader}), and due to USB device connection support not being natively available in WSL\cite{microsoft-docs-wsl-connect-usb-devices}, WSL2 must be the version installed and set, with Linux kernel 5.10.60.1 or later being ran. We can perform this setup by opening PowerShell and typing:
```PowerShell
# Install WSL
wsl --install

# Ensure the default version is set to WSL2
wsl --set-default-version 2
```
#### Smart Card Reader
TODO (includes attaching USB device, and installing `pcscd` service and device drivers + `pcsc_scan` for debugging purposes.

An example terminal output from running `pcsc_scan` in WSL and inserting the card into the smart card reader (assuming the smart card reader is attached to WSL, and `pcscd` service is running):

![Example Terminal Output From Running `pcsc_scan`](/docs/pcsc-scan-example.png)

#### Mocked SIM card
TODO (Java Card and eSIM Applet, and eSIM Loader; point to their READMEs, but include exact steps taken for this project/summary).

#### srsRAN
As noted above, our local subsystem utilizes a [modified fork of srsRAN](https://github.com/harrisonCassar/srsRAN_4G_CloudIoTManagement/tree/cloudiotmanagement) to represent a (software) mobile network infrastructure, which we install from source as follows (using a similar set of steps that can be found in the [srsRAN docs](https://docs.srsran.com/projects/4g/en/latest/general/source/1_installation.html)):

First we install srsRAN dependencies:
```bash
# The `libzmq3-dev` package is not required, but utilized in performing some testing of the srsRAN setup.
sudo apt-get install build-essential cmake libfftw3-dev libmbedtls-dev libboost-program-options-dev libconfig++-dev libsctp-dev libzmq3-dev
```

Then we download/clone the modified fork of srsRAN, and build the srsRAN binaries:
```bash
# Clone the fork of the srsRAN 4G repo, and checkout the branch that contains the CloudIoTManagement modifications.
git clone https://github.com/harrisonCassar/srsRAN_4G_CloudIoTManagement.git
cd srsRAN_4G_CloudIoTManagement
git checkout srsran-extension

# Build the srsRAN binaries.
mkdir build
cd build
cmake ../
make
```

Then, we add the necessary configuration files to run the srsRAN binaries with the project's expected configuration (software-simulated SIM card connected to the srsUE component, as we're connecting to the mocked SIM Java Card separately)
```bash
# Ensure the config directory has been created.
mkdir ~/.config/srsran

# Copy the exact configuration files that's expected by this project (`ue.conf`, `epc.conf`, `enb.conf`, and `user_deb.csv`).
cp config/* ~/.config/srsran
```

### Cloud Subsystem
To perform the setup/deployment of our cloud subsystem in Docker locally (non-cloud hosted), the process is very simple! We utilize `docker compose`. Simply put, install Docker Compose, which can be accomplished by installing Docker Desktop to your machine. See the following article for the download and/or other options for installing Docker Compose: https://docs.docker.com/compose/install/. **NOTE: We reccomend installing v4.25+ to avoid a possible memory leak bug in Docker (see below).**

For instructions on how to start up the cloud subsystem's Docker containers, refer to the [below section](#to-run) about running the project.

#### Without Docker (Locally/Natively)
**NOTE: THIS METHOD OF DEVELOPMENT, TESTING, AND DEPLOYMENT HAS BEEN DEPRECATED! Please instead refer to the above section for setup in Docker containers.**
To setup the local deployment, each subsystem involves a slightly different means/set of dependencies. To run the individual code, follow the setup/run instructions in the READMEs found within the various subdirectories. For example, for the Main Python Flask server, refer to `flask-app\README.md`.

#### Quirks
##### Kafka Topic Non-Existent on Startup
Sometimes, when starting up fresh Docker containers of the cloud subsystem components, the UDP Server will fail with an error: "When reading a Downstream Request message from Kafka: KafkaError{code=UNKNOWN_TOPIC_OR_PART,val=3,str="Subscribed topic not available: downstream-request: Broker: Unknown topic or partition"}". This is caused from the UDP Server, on startup, attempting to subscribe to the "downstream-request" topic (which is produced by the Main Flask server) however since the Kafka instance has been freshly-built, it has yet to create the topic (no messages have been produced yet for this topic).

There is a way to configure Kafka within the Docker Compose file to init with a few pre-defined topics, however when attempting to do this method for this proejct, the issue did not cease to exist. At the moment, this can be worked-around by starting up the cloud subsystem, opening the Main Flask server's web application (viewable within your browser at `localhost` with the Flask server's assigned/exposed port (ex: "[http://localhost:8000/](http://localhost:8000/)")), and invoking a "Carrier Switch Request" to be sent downstream (which will create the topic within the Kafka instance). This will create the topic within the Kafka instance, which should result in everything working once again following a restart of the UDP Server before a restart of the Main Flask Server.

##### Startup Order Affecting Downstream Messages
Occasionally, upon startup, messages sent through the Kafka instance for the Carrier Switch functionality (produced from the Main Flask server, and consumed by the UDP Server) do not seem to make it through end-to-end within the cloud. Sometimes, this is due to a massive delay somewhere in Kafka's handling, and can be either waited for (upwards of a minute) or forced by sending numerous additional "Carrier Switch Requests".

Sometimes, however, still nothing makes it all the way through to the UDP Server for consuming. For these scenarios, a restart of the UDP server, followed by the Main Flask server, usually fixes things.

##### Docker for Windows Memory Leak
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

## To Run
### Local Subsystem
To run the local subsystem's various components, we need to follow a few specific steps. We summarize those components below, and summarize their steps in the following subsections:
- [Smart Card Reader Service](#smart-card-reader-service)
- [Modified srsRAN Components](#modified-srsran-components)
- [Local Python Proxy Applications](#local-python-proxy-applications)

#### Smart Card Reader Service
In order to be able to talk to the Java Card in any capacity through the smart card reader, we need to make sure the `pcscd` service is started, which we can do as such:
```
# Confirm the `pcscd` service is running.
sudo service pcscd start # or restart
```

**NOTE**: You may need to "restart" the `pcscd` service (instead of just "start"ing it) following an attach/detachment of the smart card reader through WSL, or a machine power-cycle/restart.

#### Modified srsRAN Components
To run the srsRAN-related components, we run the following commands IN-ORDER (starting a network namespace for the UE, and then running the srsEPC (core network), srsENB (base station), and srsUE (UE), respectively):
```bash
# Ensure a network namespace exists for the UE (can check its existence with `sudo ip netns list`).
sudo ip netns add ue1

# Run srsEPC.
sudo ./srsepc/src/srsepc

# Run srsENB.
./srsenb/src/srsenb --rf.device_name=zmq --rf.device_args="fail_on_disconnect=true,tx_port=tcp://*:2000,rx_port=tcp://localhost:2001,id=enb,base_srate=23.04e6"

# Run srsUE.
sudo ./srsue/src/srsue --rf.device_name=zmq --rf.device_args="tx_port=tcp://*:2001,rx_port=tcp://localhost:2000,id=ue,base_srate=23.04e6" --gw.netns=ue1
```

Following this, the apps should be actively running with no errors outputted in the console logs, ready to intercept traffic meant for our externally-connected Java Card module sent from our Cloud Subsystem! A screenshot of these components up and running can be found as follows:

![srsRAN Components Running](/docs/srsran-4g-apps-running.png)

#### Local Python Proxy Applications
TODO (update once interface for proxy app has been updated)

### Cloud Subsystem
To run the suite, we use `docker compose up` at the base of this repository:
```bash
# Compose (build and run) all of the Docker Containers
# -d: OPTIONAL, can be used to run in the background.
# --build: can be omitted if you do not need to re-build any of the Docker images (no code changes).
sudo docker compose up --build
```
...and that's it! The Main Flask Server front-end should be viewable within your browser at `localhost` with the Flask server's assigned/exposed port (ex: "[http://localhost:8000/](http://localhost:8000/)"). A screenshot of the current ste of the front-end can be seen below the following notes.

**NOTE**: There exists a few quirks with the current implementation that can be addressed/worked around, as described in the above ["Quirks" section](#quirks) for the cloud subsystem setup.

**NOTE**: We recommend having Docker Desktop open to be able to easily view the currently running containers and/or their logs/statuses. However, there exists a number of individual commands to manage the running containers from the command-line (see the [Docker Docs on this topic](https://docs.docker.com/engine/reference/commandline/docker/)). For an example of these individual commands, see the associated `README.md` files for each of the Docker container sources located throughout this code base (e.g. for the Main Python Flask server, refer to `flask-app\README.md`).

![Flask Server Front-End](/docs/flask-server-frontend.png)

## Port Assignment
- Flask Server: 8000
- Zookeeper: 2181
- Kafka: 29092 (Docker containers), 9092 (host), 9101
- Grafana: 3000
- UDP Server: 6001
- Modem Client: 6002 (integrated within srsRAN; locally hosted, not in Docker container)
  - Proxy in native Windows: 6002 (receives UDP server traffic, forwards to WSL proxy)
  - Proxy in WSL: 6003 (receives native Windows proxy traffic, forwards to Modem Client integrated within srsRAN)

## Cloud SSH Steps
**NOTE: With the original project implementation, this was our primary means of deployment for our cloud subsystem. However, during this project's first extension, local deployment using Docker was favored instead for quicker development.**
Steps to follow to be able to `ssh` into the cloud-hosted Linux machine that is running our latest deployment of the cloud subsystem:
- Acquire key in file "cs219-instance-2.pem" (keep in root directory and DO NOT COMMIT)
- Run below commands.
`chmod 400 cs219-instance-2.pem`
`ssh -i "cs219-instance-2.pem" ubuntu@ec2-34-211-7-98.us-west-2.compute.amazonaws.com`
