# syntax=docker/dockerfile:1.4

# Adapted from:
# - https://blog.logrocket.com/build-deploy-flask-app-using-docker/
# - https://docs.docker.com/samples/flask/

# Pull Python image.
FROM --platform=$BUILDPLATFORM python:3.10-alpine AS builder

# Copy the requirements file into the image.
COPY ./udp_server/requirements.txt /app/requirements.txt

# Install Python dependencies/packages
RUN --mount=type=cache,target=/root/.cache/pip \
    pip3 install -r /app/requirements.txt

# Copy all UDP-server content to image.
COPY ./udp_server /app

# Copy dependencies content to image.
COPY ./common /app/common

# Expose all ports that we expect to receive traffic on (from other containers).
EXPOSE 6001/udp

# Config container to run in executed manner.
ENTRYPOINT ["python3"]

CMD [\
    "/app/sim_udp_server.py", \
    "--server-address", "udp_server",\
    "--server-port", "6001",\
    "--modem-address", "modem_mock",\
    "--modem-port", "6002",\
    "--streaming-address", "udp_server",\
    "--streaming-port", "8002",\
    "--log-level", "DEBUG"]