docker pull neo4j:latest

# see https://neo4j.com/developer/docker-run-neo4j/#docker-run
# NEO4J_AUTH is <user>/<password>
#   --env NEO4J_dbms_security_auth_enabled=false \
docker run --detach \
  --name mira-dkg-demo \
  -p 7474:7474 -p 7687:7687 \
  --env NEO4J_AUTH=neo4j/alpine \
  neo4j:latest

# python -m mira.dkg.construct graphs
python -m mira.dkg.construct load --no-restart

# need to restart to reload data that was just imported
docker exec (docker ps --filter "name=mira-dkg-demo" -q) neo4j restart

# since neo4j got stopped this exits the container
docker start (docker ps --filter "name=mira-dkg-demo" -aq)

docker commit \
    -a "Charles Tapley Hoyt <cthoyt@gmail.com>" \
    -m "Updated MIRA domain knowledge graph" \
    (docker ps --filter "name=mira-dkg-demo" -q) \
    cthoyt/mira-dkg-demo:latest

docker push cthoyt/mira-dkg-demo:latest
