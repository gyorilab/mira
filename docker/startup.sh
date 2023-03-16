#!/bin/bash
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
