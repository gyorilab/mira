FROM python:3.10

ARG MIRA_NEO4J_URL

RUN python -m pip install git+https://github.com/indralab/mira.git@dockerize-dkg#egg=mira[web,gunicorn]

ENTRYPOINT python -m mira.dkg.wsgi --port 5000 --host "0.0.0.0" --with-gunicorn
