# FDE-Hike

## Plan

> Find the best experience / popularity from a particular hike (i.e. cool bridges, snow, mortal accidents and similar) and thus similarity between the hikes.
> Also add columns like "danger" based on specific finite and arbitrary keywoards that could be expanded.
CHANGE THIS :)
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


# Report (in progress)
The production graph database is structured in such a way that each hike is its own node. It can be connected to many of the following node types:
- "Difficulty" (Very Easy, Easy, Moderate, Difficult, Very Difficult) : An expression of the difficulty of the hike.
- "*Keyword*" : Key words extracted by Natural Language Processing from reddit posts. One hike be connected to many keywords. 
- "Ranking" : Ranges from 1 to 5 stars
- "Region" : The region where the hike is located in.
- "Time" : The best time of day to perform the hike.
- Keyword_avg

*Keyword* and Keyword_avg are the most interesting of these Nodes since, not only do they come from analyzing the posts, but the carried sentiment of each post content and comments, creating a new node for each keyword found, repeting if found more than once as each one carries a sentiment, by the end, we run a pattern match to compute the average sentiment of one keyword's sentiment, create the new nodes called {keyword}_avg of type "Keyword_avg" to contribute to the final analysis of the graph.


# Queries to run
N.b: Queries were run with REDDIT_API_POST_LIMIT = 2, for the sake of simplicity and transmitting the idea behind the queries, as well as clear graphical representation. Feel free to tune REDDIT_API_POST_LIMIT. You can also add your own keyword files to the keywords folder and they will be automatically added to the graph database. Name it however you wish and that'll be the name of the relationship. The keywords file must be a .csv file with comma-separated keywords.

1. Retrieve all Connected Nodes for a Hike:

```cypher
MATCH (hike:Hike {name: 'Blanca Lake & Peak'})-[*1]-(connectedNode)
RETURN hike, connectedNode;
```
![Retrieve all Connected Nodes for a Hike](./static/1.png)
This query retrieves all nodes connected to the 'Blanca Lake & Peak' hike, regardless of relationship type.

2. Retrieve Nodes Related to Nature for a Hike:
```cypher
MATCH (hike:Hike {name: 'Blanca Lake & Peak'})-[:nature]-(connectedNode)
RETURN hike, connectedNode;
```

Output:
![Retrieve Nodes Related to Nature for a Hike](./static/2.png)

This query retrieves nodes related to the 'Blanca Lake & Peak' hike specifically connected through the 'nature' relationship.
Note that every node has a sentiment attatched to it, ranging from -1 to 1. We've defined the boundaries to be the following
-1 to -0.25 : a negative sentiment
-0.25 to 0.25 : a neutral sentiment
0.25 to 1 : a positive sentiment

3. Retrieve Average Sentiment Nodes Related to Nature for a Hike:
```cypher
MATCH (hike:Hike {name: 'Blanca Lake & Peak'})-[:nature_avg]-(connectedNode)
RETURN hike, connectedNode;
```
![Retrieve Average Sentiment Nodes Related to Nature for a Hike](./static/3.png)
This query retrieves nodes representing the average sentiment related to nature for the 'Blanca Lake & Peak' hike.
As one can observe, the landscape average relation is also present since the keywords sets overlap each other. 
This query cleans up the graph and gives concrete information about the sentiment of the elements in the hike.

4. Retrieve Hikes with Difficulty Level:

```cypher
MATCH (hike:Hike)-[:has_difficulty]->(difficulty:Difficulty)
WHERE difficulty.level = 'Moderate'
RETURN hike, difficulty;
```
![Retrieve Hikes with Difficulty Level](./static/4.png)
This query retrieves hikes and their associated difficulty level.

5. Retrieve Hikes with a Specific Ranking:

```cypher
MATCH (hike:Hike)-[:ranked]->(ranking:Ranking)
WHERE ranking.value = "☆☆☆☆☆"
RETURN hike, ranking;
```
![Retrieve Hikes with a Specific Ranking](./static/5.png)

This query retrieves hikes with a specific ranking (5 stars in this example).

6. Retrieve Hikes in a Certain Region:

```cypher
MATCH (hike:Hike)-[:located_in]->(region:Region)
WHERE region.name = 'Whistler'
RETURN hike, region;
```
![Retrieve Hikes in a Certain Region](./static/6.png)
This query retrieves hikes located in a specific region (Pacific Northwest in this example). Adjust the region name accordingly.

7. Retrieve Hikes Suitable for a Specific Time:
```cypher
MATCH (hike:Hike)-[:best_time]->(time:Time)
WHERE time.hours = '6 – 8'
RETURN hike, time;
```
![Retrieve Hikes Suitable for a Specific Time](./static/7.png)
This query retrieves hikes recommended for a specific time of day (8-10 / Morning in this example). Modify the time name as needed.

8. Retrieve Keywords and Their Sentiment for a Hike:
```cypher
MATCH (hike:Hike {name: 'Blanca Lake & Peak'})-[:nature]->(keyword:Keyword)
RETURN hike, keyword.name, keyword.sentiment;
```
![Retrieve Keywords and Their Sentiment for a Hike](./static/8.png)
This query retrieves keywords and their sentiment for a specific hike ('Example Hike' in this example).

9. Retrieve Average Sentiment for All Keywords Across Hikes:
```cypher
MATCH (avgKeyword:Keyword_avg)
RETURN avgKeyword.name, avgKeyword.sentiment;
```
![Retrieve Average Sentiment for All Keywords Across Hikes](./static/9.png)
This query retrieves the average sentiment for all keywords across all hikes.

10. Retrieve Hikes with Overall Positive Sentiment on a certain topic:
```cypher
MATCH (hike:Hike)-[:animals_avg]->(avgKeyword:Keyword_avg)
WHERE avgKeyword.sentiment_discrete = 'positive_sentiment'
RETURN hike, avgKeyword;
```
![Retrieve Hikes with Overall Positive Sentiment on a certain topic](./static/10.png)
This query retrieves hikes associated with keyword topics that have an overall positive sentiment.
In this case with the topic of animals. From this we can infer that the hike "Blackcomb Peak & The Spearhead" has birds and since
"birds" has an average sentiment of ~0.6 or, a "positive_sentiment", then we can safely assume that it is good for bird watching



## How to run

Run the Docker daemon, then...

## Automatic startup
### MacOS / Linux 
```sh
./start.sh
```

If you get a permission error, check the current permissions of the start.sh script
```sh
ls -l start.sh
```

If the script doesn't have execute permissions, you can add them using the chmod command
```sh
chmod +x start.sh
```

You should then be able to run the initial command.

## Manual Startup (all)


Now edit or create an **.env** file like so
```
AIRFLOW_UID=


_AIRFLOW_WWW_USER_USERNAME=airflow
_AIRFLOW_WWW_USER_PASSWORD=airflow
AIRFLOW_GID=0
_PIP_ADDITIONAL_REQUIREMENTS=xlsx2csv==0.7.8 faker==8.12.1 praw==7.7.1
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




docker-compose up -d --no-deps --build flask-app


talk about nlp import bert model challenges
talk about REDDIT_API_POST_LIMIT

BERT models have a maximum token limit, and our input text is sometimes longer than this limit (when someone comments their heart out), so we would encounter an error. In this case the model's maximum sequence length of 512. Since practically we've only found comments to go as far as 700 characters, we have truncated it, however another, better, solution that we would implement if this were to be a real commercial project, would be to truncate the comment to the maximum length of the model, and then run the model on the truncated comment, and then run the model on the next truncated comment, and so on, effectively analyzing by chunks. Or we could simply use another bert model that accepts more tokens.