# FDE-Hike

## Plan

> Find the best experience / popularity from a particular hike (i.e. cool bridges, snow, mortal accidents and similar) and thus similarity between the hikes.
> Also add columns like "danger" based on specific finite and arbitrary keywoards that could be expanded.

1. We'll call the reddit api / website to get posts from the region / location / hike name and their headlines for key examples of what to expect in the hike.
    1. We'll use key words (extracted by Natural Language Processing, NLP) in the headlines / bodies / comments to display information about what to expect on the hike: (i.e. Cool bridges, snow, mortal accidents and similar).
    2. Sentiment analysis to see the general feeling of the text and use to rank the hike.
    3. We'll use reddit labels and popularity (upvotes, comments and such) to recommend or select the best hike.
2. We'll develop a mathematical formula for the hike popularity / best experience based on the initial dataset and the scraped data.
3. Add columns like "danger" based on specific finite and arbitrary keywoards that could be expanded.
5. Add column with state or region so we can get closest or region specific hikes. Add emergency contacts based on this (?)
6. With the data we've collected we'll find the similarity between the hikes. -> ?
7. Hypothesise, then implement and then compare performance loss or improvement from a relational database to a graph database.


Graph Database for Similarity: Consider using a graph database to establish relationships between hikes, regions, and features. This can help in finding similarities between hikes and suggesting alternatives based on user preferences.


## How to run

## Automatic startup (macos/linux)
`./start.sh`

If you get a permission error, first, check the current permissions of the start.sh script
`ls -l start.sh`

If the script doesn't have execute permissions, you can add them using the chmod command
`chmod +x start.sh`

You should then be able to run the initial command

## Manual Startup (all)


Now edit or create an **.env** file like so
```
AIRFLOW_UID=


_AIRFLOW_WWW_USER_USERNAME=airflow
_AIRFLOW_WWW_USER_PASSWORD=airflow
AIRFLOW_GID=0
_PIP_ADDITIONAL_REQUIREMENTS=xlsx2csv==0.7.8 faker==8.12.1
```
Make sure to fill in the missing AIRFLOW_UID value with your local user id `id -u`.


Run the following command to creat the volumes needed in order to send data to airflow:
```sh
mkdir -p ./dags ./logs ./plugins
```

And this **once**:
```sh
docker-compose up airflow-init
```
If the exit code is 0 then it's all good.

### Running

```sh
docker-compose up
```

After it is up, add a new connection:

* Name - postgres_default
* Conn type - postgres
* Host - localhost
* Port - 5432
* Database - airflow
* Username - airflow
* Password - airflow