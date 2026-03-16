docker run --publish=7474:7474 --publish=7687:7687 --volume=neo_data:/data --env=NEO4J_AUTH=neo4j/12345678oo --env NEO4J_PLUGINS='["apoc"]' -d neo4j

