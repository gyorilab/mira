#!/bin/bash

docker build --tag mira_epi_dkg:latest .
mkdir -p mounted_graph_storage
docker run --detach -v ./mounted_graph_storage:/graphs -p 7474:7474 -p 8771:8771 -p 7687:7687 -e MIRA_NEO4J_URL=bolt://0.0.0.0:7687 --name mira mira_epi_dkg:latest