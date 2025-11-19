docker build -f Dockerfile -t mira_epi_dkg:base .

docker build -f Dockerfile.full -t mira_epi_dkg:full .

# Either edit this line to add OPENAI_API_KEY env variable or export it in container
docker run --detach -p 8771:8771 -p 7687:7687 -e MIRA_NEO4J_URL=bolt://0.0.0.0:7687 --name mira mira_epi_dkg:full
