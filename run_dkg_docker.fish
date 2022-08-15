docker pull cthoyt/mira-dkg-demo:latest

docker run --detach \
  --name mira-dkg-demo \
  -p 8600:7474 -p 8601:7687 \
  --env NEO4J_AUTH=neo4j/alpine \
  cthoyt/mira-dkg-demo:latest

# python -m mira.dkg.construct graphs
python -m mira.dkg.summarize \
    --url bolt://0.0.0.0:7687 \
    --user neo4j \
    --password alpine
