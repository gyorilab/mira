# Docker

This folder contains Docker build procedures for various aspects of MIRA.

## MIRA Front-end

This folder implements a Docker build procedure for building a neo4j instance
of MIRA's domain knowledge graph from a given node and edge dump. The node
and edge dumps are assumed to be available as gzipped TSV files called
`nodes.tsv.gz` and `edges.tsv.gz` in this folder. The build can be done as

```shell
docker build --tag mira_dkg:latest .
```

Once the build finished, you can run the container locally as

```shell
docker run -d -p 8771:8771 -e MIRA_NEO4J_URL=bolt://0.0.0.0:7687 mira_dkg:latest
```

This exposes a REST API at `http://localhost:8771`. Note that the `-d` flag
runs the container in the background.

## MIRA Metaregistry

You can build the metaregistry with:

```shell
docker build --file metaregistry.Dockerfile --tag mira_metaregistry:latest .
```

Once the build finished, you can run the container locally as:

```shell
docker run --detach -p 8772:8772 -e MIRA_NEO4J_URL=bolt://0.0.0.0:7687 mira_metaregistry:latest
```
