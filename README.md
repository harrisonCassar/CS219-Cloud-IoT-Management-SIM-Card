# Cloud-Based IoT Management with SIM Card
The code here was developed as a part of the course project for CS219: Cloud Computing with Professor Songwu Lu. Guidance for the project was graciously provided by Mentor Jinghao Zhao.

## Basic Overview
For our "local" system, we have the following main components:
- Javacard-eSIM applet
- Python modem client (emulates modem that uses the SIM card)

For our "cloud" system, we have the following main components:
- Python UDP server (mediates communication between the Python modem client and the main cloud server)
- Main Python Flask server (manages/accumulates/processes all IoT data for storage and front-end display, as well as expose functionality to perform carrier switches on SIM card)

## Setup
To setup the local deployment, each subsystem involves a slightly different means/set of dependencies. To run the individual code, follow the setup/run instructions in the READMEs found within the various subdirectories. For example, for the Main Python Flask server, refer to `flask-app\README.md`.

**NOTE:** Eventually, we desire to move the cloud-related servers to Docker containers, but for now we do a simple "deploy" on an already-setup environment/device.

## Port Assignment
Flask Server: 8000
UDP Server: 6001
Modem Client: 6002