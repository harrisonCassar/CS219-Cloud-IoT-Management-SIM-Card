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

# Copy all Kafka-consumer content to image.
COPY ./test/kafka_consumer /app

# Copy dependencies content to image.
COPY ./common /app/common

# Config container to run in executed manner.
ENTRYPOINT ["python3"]

CMD [\
    "/app/kafka_consumer.py",\
    "--topics", "imu", "gyro", "temp",\
    "--kafka-address", "kafka",\
    "--kafka-port", "29092",\
    "--log-level", "INFO"]