# syntax=docker/dockerfile:1.4

# Adapted from:
# - https://blog.logrocket.com/build-deploy-flask-app-using-docker/
# - https://docs.docker.com/samples/flask/

# Pull Python image.
FROM --platform=$BUILDPLATFORM python:3.9-bullseye AS builder

# Copy the requirements file into the image.
COPY ./modem/requirements.txt /app/requirements.txt

# Install Python dependencies/packages
# RUN apk add --no-cache gcc
# RUN apk update && apk add swig pcsclite-dev
RUN apt-get update && apt-get install -y swig
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpcsclite-dev \
    && rm -rf /var/lib/apt/lists/*
RUN --mount=type=cache,target=/root/.cache/pip \
    pip3 install -r /app/requirements.txt

# Copy all Modem Mock content to image.
COPY ./modem /app

# Copy dependencies content to image.
COPY ./common /app/common
COPY ./modem/sim_reader.py /app/sim_reader.py
COPY ./modem/sim_helpers.py /app/sim_helpers.py

# Expose all ports that we expect to receive traffic on (from other containers).
EXPOSE 6002/udp

# Config container to run in executed manner.
ENTRYPOINT ["python3"]

CMD [\
    "/app/modem.py", \
    # "--modem-address", "modem_mock",\
    "--modem-port", "6002",\
    # "--server-address", "udp_server",\
    "--server-port", "6001",\
    "--log-level", "DEBUG"]