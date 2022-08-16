FROM python:3.10

ARG MIRA_NEO4J_URL

RUN python -m pip install git+https://github.com/indralab/mira.git@dockerize-dkg#egg=mira[web,gunicorn]

ENTRYPOINT python -m mira.dkg.wsgi
