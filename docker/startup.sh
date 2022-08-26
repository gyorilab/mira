#!/bin/bash
neo4j start
sleep 100
neo4j status
uvicorn --host 0.0.0.0 --port 8771 mira.dkg.wsgi:app
