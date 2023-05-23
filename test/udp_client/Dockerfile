# syntax=docker/dockerfile:1.4

# Adapted from:
# - https://blog.logrocket.com/build-deploy-flask-app-using-docker/
# - https://docs.docker.com/samples/flask/

# Pull Python image.
FROM --platform=$BUILDPLATFORM python:3.10-alpine AS builder

# Copy all UDP-client content to image.
COPY ./test/udp_client /app

# Copy dependencies content to image.
COPY ./common /app/common

# Expose all ports that we expect to receive traffic on (from other containers).
EXPOSE 6002/udp

# Config container to run in executed manner.
ENTRYPOINT ["python3"]

CMD [\
    "/app/udp_client.py", \
    "--remote-address", "172.17.0.3",\
    "--remote-port", "6001",\
    "--local-address", "127.0.0.1",\
    "--local-port", "6002",\
    "--log-level", "DEBUG"]

# TODO: Avoid hardcoding IP addresses. Perhaps use Docker's built-in networking functionality and/or `docker-compose`?
# ENTRYPOINT [\
#     "python3", "./app/udp_client.py",\
#     "--remote-address", "172.17.0.3",\
#     "--remote-port", "6001",\
#     "--local-address", "127.0.0.1",\
#     "--local-port", "6002",\
#     "--log-level", "DEBUG"]