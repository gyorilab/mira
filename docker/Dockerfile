FROM ubuntu:focal

WORKDIR /sw

# Install and configure neo4j and python environment
RUN apt-get update && \
    apt-get install -y apt-transport-https ca-certificates curl wget software-properties-common && \
    curl -fsSL https://debian.neo4j.com/neotechnology.gpg.key | apt-key add - && \
    add-apt-repository "deb https://debian.neo4j.com stable 4.4" && \
    apt-get install -y neo4j && \
    apt-get install -y git zip unzip bzip2 gcc graphviz graphviz-dev \
        pkg-config python3 python3-pip && \
    # purge blinker here to avoid pip uninstall error below
    apt-get purge -y python3-blinker && \
    ln -s /usr/bin/python3 /usr/bin/python

ARG version=2023-10-19
ARG domain=climate
ARG embeddings_path=/sw/embeddings.tsv.gz
# This latter is used in the code
ENV MIRA_DOMAIN=${domain}
ENV EMBEDDINGS_PATH=${embeddings_path}

# Download graph content and ingest into neo4j
RUN wget -O /sw/nodes.tsv.gz https://askem-mira.s3.amazonaws.com/dkg/$domain/build/$version/nodes.tsv.gz && \
    wget -O /sw/edges.tsv.gz https://askem-mira.s3.amazonaws.com/dkg/$domain/build/$version/edges.tsv.gz && \
    wget -O $embeddings_path https://askem-mira.s3.amazonaws.com/dkg/$domain/build/$version/embeddings.tsv.gz && \
    sed -i 's/#dbms.default_listen_address/dbms.default_listen_address/' /etc/neo4j/neo4j.conf && \
    sed -i 's/#dbms.security.auth_enabled/dbms.security.auth_enabled/' /etc/neo4j/neo4j.conf && \
    neo4j-admin import --delimiter='TAB' --skip-duplicate-nodes=true --skip-bad-relationships=true --nodes /sw/nodes.tsv.gz --relationships /sw/edges.tsv.gz

# Python packages
RUN python -m pip install --upgrade pip && \
    python -m pip install git+https://github.com/gyorilab/mira.git@main#egg=mira[web,uvicorn,dkg-client] && \
    python -m pip uninstall -y flask_bootstrap && \
    python -m pip uninstall -y bootstrap_flask && \
    python -m pip install bootstrap_flask && \
    python -m pip install --no-dependencies pint && \
    python -m pip install --no-dependencies "lxml>=4.6.4" && \
    python -m pip install --no-dependencies --ignore-requires-python sbmlmath

# Copy the example json for reconstructing the ode semantics
RUN wget -O /sw/sir_flux_span.json https://raw.githubusercontent.com/gyorilab/mira/main/tests/sir_flux_span.json

COPY startup.sh startup.sh
ENTRYPOINT ["/bin/bash", "/sw/startup.sh"]
