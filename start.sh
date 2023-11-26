#!/bin/bash

# Create .env file if it doesn't exist
# Automatically assign local user id
# Add additional pip requirements
FILE=./.env
if [ ! -f "$FILE" ]; then
sh -c "
cat <<EOF >>./.env
AIRFLOW_UID=$(id -u) 


_AIRFLOW_WWW_USER_USERNAME=airflow
_AIRFLOW_WWW_USER_PASSWORD=airflow
AIRFLOW_GID=0
_PIP_ADDITIONAL_REQUIREMENTS=xlsx2csv==0.7.8 faker==8.12.1 tensorflow==2.13.1 praw==7.7.1 py2neo==2021.2.4 requests==2.28.1 apache-airflow-providers-mongo==2.3.1 pandas==2.0.3 beautifulsoup4==4.12.2 transformers==4.35.2 spacy==3.7.2 https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.0/en_core_web_sm-3.7.0.tar.gz
EOF
"
fi

# Build images
# docker build -f ./path/to/Dockerfile -t name_of_process ./run_this

# Initialize the database
# On all operating systems, you need to run database migrations and create the first user account.
# Run ONCE, if exit code is 0 then success
docker compose up airflow-init

# Start all services (detached/background mode)
docker compose -f docker-compose.arm64.yaml up --build --force-recreate -d

# Add connections
docker compose exec airflow-webserver airflow connections add 'postgres_default' --conn-uri 'postgres://airflow:airflow@postgres:5432/airflow'
docker compose exec airflow-webserver airflow connections add 'mongo_default' --conn-uri 'mongodb://mongo:27017'
# docker compose exec airflow-webserver airflow connections add 'neo4j_default' --conn-uri 'bolt://neo:7687'