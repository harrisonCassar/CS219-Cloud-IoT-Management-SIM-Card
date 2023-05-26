# UDP Client
This directory encompasses all of the necessary code for a basic UDP client, which can be used for testing the UDP server (and any other UDP clients/servers).

## Setup/Run/Manage in Docker Container
**NOTE: In order to test with this within the full system, first refer to the steps using `docker compose` outlined in the main `README.md` in the root directory. Then, stop the specific subsystem you're looking to mock out, and then config/build/run this Docker container to effectively replace this subsystem.**

Follow the below steps to setup, run, and manage the server in a Docker container.

```bash
# Download and install Docker.
# See the documentation: https://docs.docker.com/get-docker/.

# Open Docker Desktop

# Check you've successfully installed docker.
`docker --help`

# Build image (only needs to be done after modifying installed dependencies and/or OS-level package versions).
`cd /` # root directory, so that Docker's context is at the top-level to allow copying of the `common` directory.
`docker image build -t kafka_consumer -f test/kafka_consumer/Dockerfile .` # -t: Name to be given to built image

# Run the container (if container does not exist yet and/or image is different)
`docker run --rm --name kafka_consumer -it kafka_consumer` # specify option -d to run in detached mode; -i stands for interactive mode, -t will allocate a psuedo terminal for us

# To start/stop/restart a docker container with our image:
`docker restart kafka_consumer`
`docker stop kafka_consumer`
`docker start kafka_consumer`

# To remove a container:
`docker rm kafka_consumer` # use the --force option to remove running containers

# To remove all stopped containers:
`docker container prune`

# To view all available Docker images:
`docker image list`

# To view all running Docker containers:
`docker ps`

# To view IP address for running Docker container:
`docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' kafka_consumer`
```

## Setup/Run/Manage locally without Docker Container
**NOTE: THIS METHOD OF DEVELOPMENT, TESTING, AND DEPLOYMENT HAS BEEN DEPRECATED! Please instead refer to the above section for steps on how to setup/run/manage the application in a Docker container.**

This can also be run locally by just invocating it via the command line at the root directory with the proper arguments.