FROM ubuntu:20.04

WORKDIR /sw

COPY startup.sh startup.sh
COPY edges.tsv.gz edges.tsv.gz
COPY nodes.tsv.gz nodes.tsv.gz

RUN apt-get update && \
    apt-get install -y apt-transport-https ca-certificates curl software-properties-common && \
    curl -fsSL https://debian.neo4j.com/neotechnology.gpg.key | apt-key add - && \
    add-apt-repository "deb https://debian.neo4j.com stable 4.4" && \
    apt-get install -y neo4j

RUN sed -i 's/#dbms.default_listen_address/dbms.default_listen_address/' /etc/neo4j/neo4j.conf && \
    sed -i 's/#dbms.security.auth_enabled/dbms.security.auth_enabled/' /etc/neo4j/neo4j.conf && \
    neo4j-admin import --delimiter='TAB' --skip-duplicate-nodes=true --skip-bad-relationships=true --nodes /sw/nodes.tsv.gz --relationships /sw/edges.tsv.gz

RUN apt-get install -y git wget zip unzip bzip2 gcc graphviz graphviz-dev \
        pkg-config python3 python3-pip && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    python -m pip install git+https://github.com/indralab/mira.git@dockerize-dkg#egg=mira[web,gunicorn] && \
    python -m pip uninstall -y flask_bootstrap && \
    python -m pip uninstall -y bootstrap_flask && \
    python -m pip install bootstrap_flask

ENTRYPOINT ["/bin/bash", "/sw/startup.sh"]
