#!/bin/bash
neo4j start
sleep 5
gunicorn --bind 0.0.0.0:8771 mira.dkg.wsgi:app
