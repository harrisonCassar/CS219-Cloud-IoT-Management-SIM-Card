# syntax=docker/dockerfile:1.4

# Adapted from:
# - https://blog.logrocket.com/build-deploy-flask-app-using-docker/
# - https://docs.docker.com/samples/flask/

# Pull Python image.
FROM --platform=$BUILDPLATFORM python:3.10-alpine AS builder

# Install Kafka Dependencies (needed before installing the Python Kafka library `confluent-kafka`).
RUN apk update && apk add python3-dev \
                        gcc \
                        libc-dev
RUN sed -i -e 's/v3.4/edge/g' /etc/apk/repositories \
    && apk upgrade --update-cache --available \
    && apk add --no-cache librdkafka-dev python3-dev

# Copy the requirements file into the image.
COPY ./udp_server/requirements.txt /app/requirements.txt

# Install Python dependencies/packages.
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
    "--kafka-address", "kafka",\
    "--kafka-port", "29092",\
    "--flask-server-address", "flask_server",\
    "--flask-server-port", "8000",\
    "--streaming-address", "grafana",\
    "--streaming-port", "3000",\
    "--log-level", "INFO"]
