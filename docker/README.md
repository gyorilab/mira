# Docker

This folder contains Docker build procedures for various aspects of MIRA.

## MIRA Front-end

This folder implements a Docker build procedure for building a neo4j instance
of MIRA's domain knowledge graph from a given node and edge dump. The node
and edge dumps are pulled from S3.

```shell
docker build --tag mira_dkg:latest .
```

If you want to test with local files, put `nodes.tsv.gz` and `edges.tsv.gz` in
this folder and use:

```shell
# Get graph data
export DOMAIN=epi
cp ~/.data/mira/$DOMAIN/nodes.tsv.gz nodes.tsv.gz
cp ~/.data/mira/$DOMAIN/edges.tsv.gz edges.tsv.gz

# Build docker
docker build --file Dockerfile.local --tag mira_dkg:latest .
```

Once the build finished, you can run the container locally as

```shell
docker run -d -p 8771:8771 -e MIRA_NEO4J_URL=bolt://0.0.0.0:7687 --name mira_dkg mira_dkg:latest
```

This exposes a REST API at `http://localhost:8771`. Note that the `-d` flag
runs the container in the background. If you want to expose Neo4j's bolt port, also
add `-p 7687:7687`.

## MIRA Metaregistry

You can build the metaregistry with:

```shell
docker build --file Dockerfile.metaregistry --tag mira_metaregistry:latest .
```

Once the build finished, you can run the container locally as:

```shell
docker run --detach -p 8772:8772 --name mira_metaregistry mira_metaregistry:latest
```

Optionally, add the arguments `-e ROOT_PATH='/prefix'` and/or `-e BASE_URL=d1t1rcuq5sa4r0.cloudfront.net` to run the
metaregistry under a path prefix and/or changing the api-docs base url, respectively. This is useful e.g. when
deploying the metaregistry together with other resources behind a proxy (Cloud Front, load balancer + nginx, etc):

```shell
docker run --detach -p 8772:8772 -e ROOT_PATH='/reg' -e BASE_URL=d1t1rcuq5sa4r0.cloudfront.net mira_metaregistry:latest
```

## Important Note on Path Prefix Behavior

Both the domain knowledge graph and the metaregistry are able to run with path prefixes. They do however behave 
differently in one very important aspect: the domain knowledge graph app, which runs on FastAPI, assumes that the 
proxy strips the path prefix, while the metaregistry app, which runs with Flask does not. The main reason for this is 
that FastAPI has a simple setting that turns on 'path prefix'-mode and sets up the API and the swagger documentation 
to automatically assume this
(see more [here](https://fastapi.tiangolo.com/advanced/behind-a-proxy/#proxy-with-a-stripped-path-prefix)). For Flask 
on the other hand, there is no single place that does all the setup, and the dependencies for the metaregistry 
currently makes it rather difficult to do this. For now, the setup simply adds a path prefix and the app will then run 
assuming the proxy doesn't strip the prefix.

To summarize:

DKG app, when using path prefix:
```text
Browser on https://d1t1rcuq5sa4r0.cloudfront.net/prefix/path -> 
Proxy on http://0.0.0.0:1234/prefix/path -> 
Server on http://0.0.0.0:8771/path
```

Metaregistry app, when using path prefix:
```text
Browser on https://d1t1rcuq5sa4r0.cloudfront.net/prefix/path -> 
Proxy on http://0.0.0.0:1234/prefix/path -> 
Server on http://0.0.0.0:8772/prefix/path
```
