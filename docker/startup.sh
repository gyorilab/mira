#!/bin/bash

set -eoxu pipefail

echo "Starting database"
neo4j start

echo "Waiting for database"
until [ \
  "$(curl -s -w '%{http_code}' -o /dev/null "http://localhost:7474")" \
  -eq 200 ]
do
  sleep 5
done

neo4j status

# Index nodes on id property
python -m mira.dkg.indexing --exist-ok

# Set ROOT_PATH to empty string if it is not set in the environment
ROOT_PATH="${ROOT_PATH:-}"

# Start the service

if [ "${ROOT_PATH}" ]; then
  echo "Running with root path set to ${ROOT_PATH}"
  uvicorn --host 0.0.0.0 --port 8771 mira.dkg.wsgi:app --root-path "${ROOT_PATH}"
else
  echo 'No root path set in environment, running at "/"'
  uvicorn --host 0.0.0.0 --port 8771 mira.dkg.wsgi:app
fi
