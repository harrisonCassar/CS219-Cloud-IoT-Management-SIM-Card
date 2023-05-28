# Grafana
This directory contains all of the supporting files for Grafana, most importantly its config files and pre-saved dashboards.

## Setup/Run/Manage in Docker Container
Please refer to the steps using `docker compose` outlined in the main `README.md` in the root directory.

## Update Version-Controlled Dashboards
If you make changes to the Grafana dashboards when the system is running, these will save during your session, but will be OVERRIDED each time you re-deploy the Grafana image (using `docker compose`). If you desire to save these changes into this git repo's version control, then run the provided `update-dashboards.sh` Bash script while Grafana is running to do so.