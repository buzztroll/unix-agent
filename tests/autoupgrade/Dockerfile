FROM ubuntu:14.04

RUN apt-get update && apt-get install -y curl

COPY install_agent.sh /install_agent.sh
COPY run_forever.sh /run_forever.sh
COPY upgrade.py /upgrade.py
COPY upgrade.sh /upgrade.sh


