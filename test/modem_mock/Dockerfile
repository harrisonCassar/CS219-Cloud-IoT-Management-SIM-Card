# syntax=docker/dockerfile:1.4

# Adapted from:
# - https://blog.logrocket.com/build-deploy-flask-app-using-docker/
# - https://docs.docker.com/samples/flask/

# Pull Python image.
FROM --platform=$BUILDPLATFORM python:3.10-alpine AS builder

# Copy the requirements file into the image.
COPY ./test/modem_mock/requirements.txt /app/requirements.txt

# Install Python dependencies/packages
RUN --mount=type=cache,target=/root/.cache/pip \
    pip3 install -r /app/requirements.txt

# Copy all Modem Mock content to image.
COPY ./test/modem_mock /app

# Copy dependencies content to image.
COPY ./common /app/common

# Expose all ports that we expect to receive traffic on (from other containers).
EXPOSE 6002/udp

# Config container to run in executed manner.
ENTRYPOINT ["python3"]

CMD [\
    "/app/modem_mock.py", \
    "--modem-address", "127.0.0.1",\
    "--modem-port", "6002",\
    "--server-address", "172.17.0.3",\
    "--server-port", "6001",\
    "--log-level", "DEBUG"]

# ENTRYPOINT [\
#     "python3", "/app/modem_mock.py",\
#     "--remote-address", "172.17.0.3",\
#     "--remote-port", "6001",\
#     "--local-address", "127.0.0.1",\
#     "--local-port", "6002",\
#     "--log-level", "DEBUG"]