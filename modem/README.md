# WIP
Will contain all SIM-related code, including the Python modem emulator.

## Setup/Run/Manage in Docker Container
**NOTE: Only follow the steps in this section if you're looking to run/manage this application indepedently from the other containers. If you desire to run this application as a part of the full system, please refer to the steps using `docker compose` outlined in the main `README.md` in the root directory.**
Follow the below steps to setup, run, and manage the server in a Docker container.

```bash
# Download and install Docker.
# See the documentation: https://docs.docker.com/get-docker/.

# Open Docker Desktop

# Check you've successfully installed docker.
`docker --help`

# Build image (only needs to be done after modifying installed dependencies and/or OS-level package versions).
`cd /` # root directory, so that Docker's context is at the top-level to allow copying of the `common` directory.
`docker image build -t modem -f modem/Dockerfile .` # -t: Name to be given to built image

# Run the container (if container does not exist yet and/or image is different)
`docker run --network host --name modem -p 6002\:6002/udp modem` # specify option -d to run in detached mode

# To start/stop/restart a docker container with our image:
`docker restart modem_mock`
`docker stop modem_mock`
`docker start modem_mock`

# To remove a container:
`docker rm modem_mock` # use the --force option to remove running containers

# To remove all stopped containers:
`docker container prune`

# To view all available Docker images:
`docker image list`

# To view all running Docker containers:
`docker ps`

# To view IP address for running Docker container:
`docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' modem_mock`
```
