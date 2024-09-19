#!/bin/bash

# Check if the ncbitaxon pickled graph file exists
if [ ! -f /graphs/ncbitaxon_obo_graph.pkl ]; then
  echo "Pickled ncbitaxon obo graph file not found. Generating it"
  python /sw/generate_obo_graphs.py
else
  echo "Pickled ncbitaxon obo graph file already exists in the container in
  /graphs/"
fi

neo4j start
sleep 100
neo4j status

# Index nodes on id property
python -m mira.dkg.indexing --exist-ok

# Start the service

if [ "${ROOT_PATH}" ]; then
  echo "Running with root path set to ${ROOT_PATH}"
  uvicorn --host 0.0.0.0 --port 8771 mira.dkg.wsgi:app --root-path "${ROOT_PATH}"
else
  echo 'No root path set in environment, running at "/"'
  uvicorn --host 0.0.0.0 --port 8771 mira.dkg.wsgi:app
fi
