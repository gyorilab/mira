#!/bin/bash
neo4j start
sleep 5
python -m mira.dkg.wsgi --host 0.0.0.0
