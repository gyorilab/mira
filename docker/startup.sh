#!/bin/bash
neo4j start
sleep 100
neo4j status
gunicorn --bind 0.0.0.0:8771 mira.dkg.wsgi:app
