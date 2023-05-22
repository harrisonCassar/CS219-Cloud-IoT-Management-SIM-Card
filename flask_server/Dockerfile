# syntax=docker/dockerfile:1.4

# Adapted from:
# - https://blog.logrocket.com/build-deploy-flask-app-using-docker/
# - https://docs.docker.com/samples/flask/

# Pull Python image.
FROM --platform=$BUILDPLATFORM python:3.10-alpine AS builder

# Copy the requirements file into the image.
COPY requirements.txt /app/requirements.txt

# Install Python dependencies/packages
RUN --mount=type=cache,target=/root/.cache/pip \
    pip3 install -r /app/requirements.txt

# Copy all flask-server content to image.
COPY . /app

# Config container to run in executed manner.
ENTRYPOINT ["python3"]

CMD ["/app/app.py"]