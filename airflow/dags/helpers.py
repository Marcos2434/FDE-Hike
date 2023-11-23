import praw
import json
import os
import csv
import requests
import pandas as pd

import redis
import random
import pymongo as py
from py2neo import Node, Relationship, Graph, NodeMatcher


import spacy
from collections import Counter
from bs4 import BeautifulSoup


BASE_DIR = '/opt/airflow/'
DATA_DIR = os.path.join(BASE_DIR, 'data')
KEYWORDS_DIR = os.path.join(BASE_DIR, 'keywords')

reddit_credentials = praw.Reddit(
    client_id="FmDPjXlF33v45zALJvQuEg",
    client_secret="-8egIOAFeqweAASt_NRUjVxPke5dyw",
    user_agent="hiking-app por u/Asteteh",
)

# host is the name of the service runnning in the docker file, in this case just redis
redis_client = redis.StrictRedis(host='redis', port=6379, decode_responses=True)

# connection with mongo
myclient = py.MongoClient("mongodb://mongo:27017/")
mongo_db = myclient['hiking_db']
mongo_collection_hikings = mongo_db['hikings']

#connection with neo4j
graph = Graph("bolt://neo:7687")
neo4j_session = graph.begin()

def extract_hikes_data(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', {'id': 'tablepress-2'})
        table_data = []
        headers = []

        for row in table.find_all('tr'):
            row_data = {}
            cells = row.find_all(['td', 'th'])

            if not headers:
                headers = [cell.get_text(strip=True) for cell in cells]
            else:
                for i in range(len(headers)):
                    row_data[headers[i]] = cells[i].get_text(strip=True)
                table_data.append(row_data)

        # Convert to JSON
        json_data = json.dumps(table_data, ensure_ascii=False, indent=2)
        redis_client.set('extract_hiking', json_data)

    else:
        print(f"Error: {response.status_code}")

# support function, responsible for transforming the data
def categorize_time_hours(time_hours):
    if '0 – 2' in time_hours or '2 – 4' in time_hours:
        return 'Short'
    elif '4 – 6' in time_hours or '6 – 8' in time_hours:
        return 'Medium'
    else:
        return 'Long'

# support function, responsible for transforming the data
def categorize_stars(star_rating):
    if '☆☆☆☆☆' in star_rating:
        return 'Excellent'
    elif '☆☆☆☆' in star_rating:
        return 'Very Good'
    elif '☆☆☆' in star_rating:
        return 'Good'
    elif '☆☆' in star_rating:
        return 'Fair'
    elif '☆' in star_rating:
        return 'Poor'
    else:
        return 'Unknown'

def transformation_redis_hikings(hike_key):

    data = redis_client.get(hike_key)
    hike_data_list = json.loads(data)

    for hike_data in hike_data_list:
        hike_data['TIME (HOURS)'] = categorize_time_hours(hike_data['TIME (HOURS)'])
        hike_data['RANKING'] = categorize_stars(hike_data['RANKING'])
        hike_data['ELEVATION GAIN (M)'] = hike_data['ELEVATION GAIN (M)'].replace(',', '.')

    redis_client.set(hike_key, json.dumps(hike_data_list))

def insert_mongo(hike_key):
    data = redis_client.get(hike_key)
    hike_data_list = json.loads(data)

    name_collection = 'hikings'
    if name_collection in mongo_db.list_collection_names():
        mongo_collection = mongo_db[name_collection]
        mongo_collection.drop()

    mongo_collection_hikings.insert_many(hike_data_list)


def insert_data_mongo_in_neo4j():
    # Delete all existing nodes and relationships in the Neo4j database
    graph.delete_all()

    # Recover data from MongoDB
    data = mongo_collection_hikings.find({}, {'_id': 0, 'HIKE NAME': 1, 'RANKING': 1, 'DIFFICULTY': 1, 'TIME (HOURS)': 1, 'REGION': 1})

    for hike_data in data:
        hike_name = hike_data['HIKE NAME']
        difficulty = hike_data['DIFFICULTY']
        ranking = hike_data['RANKING']
        time_hours = hike_data['TIME (HOURS)']
        region = hike_data['REGION']

        # Create node for HIKE NAME if it does not exist
        hike_node = Node("Hike", name=hike_name)
        graph.merge(hike_node, "Hike", "name")

        # Create node for DIFFICULTY if it does not exist
        difficulty_node = Node("Difficulty", level=difficulty)
        graph.merge(difficulty_node, "Difficulty", "level")

        # Create relationship between HIKE NAME and DIFFICULTY
        relation_difficulty = Relationship(hike_node, "HAS_DIFFICULTY", difficulty_node)
        graph.create(relation_difficulty)

        # Create node for RANKING if it does not exist
        ranking_node = Node("Ranking", value=ranking)
        graph.merge(ranking_node, "Ranking", "value")

        # Create relationship between HIKE NAME and RANKING
        relation_ranking = Relationship(hike_node, "HAS_RANKING", ranking_node)
        graph.create(relation_ranking)

        # Create node for TIME if it does not exist
        time_node = Node("Time", hours=time_hours)
        graph.merge(time_node, "Time", "hours")

        # Create relationship between HIKE NAME and TIME
        relation_time = Relationship(hike_node, "HAS_TIME", time_node)
        graph.create(relation_time)

        # Create node for REGION if it does not exist
        region_node = Node("Region", name=region)
        graph.merge(region_node, "Region", "name")

        # Create relationship between HIKE NAME and REGION
        relation_region = Relationship(hike_node, "HAS_REGION", region_node)
        graph.create(relation_region)

def call_reddit_api(limit, subreddit_name='all'):
    """Calls Reddit API to get the top <limit> posts for each hike in the list.

    Args:
        limit (int): Number of posts to return for each hike.
        subreddit_name (str, optional): Name of subreddit to look in. Defaults to 'all'.
    """

    data = mongo_collection_hikings.find({}, {'_id': 0, 'HIKE NAME': 1})
    hike_names = [hike_data['HIKE NAME'] for hike_data in data]

    all_hikes_keywords = {}

    for hike_name in hike_names:
        subreddit = reddit_credentials.subreddit(subreddit_name)
        search_results = subreddit.search(hike_name, limit=limit)

        top_posts = []

        for post in search_results:
            top_post = {
                "word": post.title,
                "count": post.score,
            }

            # Additional logic for comments, adjust as needed

            top_posts.append(top_post)

        # Order the main posts by count in descending order
        top_posts.sort(key=lambda x: x["count"], reverse=True)

        # Capture the top 5 posts
        posts = top_posts[:5]

        # Append null values to ensure uniform length
        while len(posts) < 5:
            posts.append({"word": None, "count": None})

        all_hikes_keywords[hike_name] = posts

    # Serialize the results in JSON format
    json_data = json.dumps(all_hikes_keywords, indent=4, ensure_ascii=False)

    # Save JSON data to a file (or use it as needed)
    with open('data/all_hikes_keywords.json', 'w') as json_file:
        json_file.write(json_data)

    print("JSON file generated successfully.")

def natural_language_processing():

    # Load the keywords
    keywords = {}
    for root, dirs, files in os.walk(KEYWORDS_DIR):
        for file in files:
            if file.endswith(".csv"):
                with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                    filename = file.split(".")[0]
                    keywords[filename] = [word.strip() for word in next(csv.reader(f))]

    nlp = spacy.load('en_core_web_sm')

    # Dictionary to store results
    all_hikes_keywords = {}

    # Loop over hikes in Redis
    for hike_key in redis_client.keys('hike*'):
        hike_name = hike_key.split(":")[1]
        hike_data = redis_client.hgetall(hike_key)
        posts = json.loads(hike_data["Hikes"])

        # Initialize keyword counter for this hike
        keyword_counter = Counter()

        # Loop over the posts in the hike and perform NLP
        for post in posts:
            for comment in post["Comments"]:
                text_to_analyze = comment["Content"]
                doc = nlp(text_to_analyze)

                # Loop over keywords in value
                for value in keywords.values():
                    for token in doc:
                        if not token.is_stop and not token.is_punct:
                            lemma = token.lemma_
                            if lemma in value:
                                keyword_counter[lemma] += 1

        # Get the 10 most frequent keywords in the post
        top_keywords = keyword_counter.most_common(10)

        # Create a list of the top keywords
        top_keywords_list = [{"word": word, "count": count} for word, count in top_keywords]

        # Add the list to the dictionary
        all_hikes_keywords[hike_name] = top_keywords_list

    # Serialize the dictionary in JSON format
    json_result = json.dumps(all_hikes_keywords, indent=4, ensure_ascii=False)

    # Save the results in a single JSON file for all hikes
    output_file_path = os.path.join(BASE_DIR, "data/all_hikes_keywords.json")
    with open(output_file_path, "w", encoding="utf-8") as f:
        f.write(json_result)


def nature_neo4j():
    data = mongo_collection_hikings.find({}, {'_id': 0, 'HIKE NAME': 1})
    hike_names = [hike_data['HIKE NAME'] for hike_data in data]

    json_data = pd.read_json('data/all_hikes_keywords.json')

    for hike_name, elements in json_data.items():
        hike_node = Node("Hike", name=hike_name)
        graph.merge(hike_node, "Hike", "name")

        for element in elements:
            # Accede a las claves "word" y "count" de cada diccionario
            word = element["word"]

            # Verifica si el nodo Nature ya existe
            nature_node = Node("Nature", type=word)
            existing_nature_node = graph.nodes.match("Nature", type=word).first()

            if existing_nature_node:
                nature_node = existing_nature_node
            else:
                graph.create(nature_node)

            # Verifica si la relación ya existe
            existing_relation = graph.match((hike_node, "HAS_NATURE", nature_node)).first()

            if not existing_relation:
                relation = Relationship(hike_node, "HAS_NATURE", nature_node)
                graph.create(relation)


def _insert():
    df = pd.read_json('data/data_hiking.json')
    with open("/opt/airflow/dags/inserts.sql", "w") as f:
        f.write(
            "DROP TABLE IF EXISTS hikings;\n"
            "CREATE TABLE IF NOT EXISTS hikings (\n"
            "    Hike_name VARCHAR(255),\n"
            "    Ranking VARCHAR(255),\n"
            "    Difficulty VARCHAR(255),\n"
            "    Distance_km DECIMAL(10, 2),\n"
            "    Elevation_gain_m DECIMAL(10, 2),\n"
            "    Gradient VARCHAR(255),\n"
            "    Time_hours VARCHAR(255),\n"
            "    Dogs VARCHAR(10),\n"
            "    _4x4 VARCHAR(255),\n"
            "    Season VARCHAR(255),\n"
            "    Region VARCHAR(255)\n"
            ");\n"
        )

        for index, row in df.iterrows():
            hike_name = row['HIKE NAME']
            ranking = categorize_stars(row['RANKING'])
            difficulty = row['DIFFICULTY']
            distance_km = row['DISTANCE (KM)']
            elevation_gain_m = row['ELEVATION GAIN (M)']
            gradient = row['GRADIENT']
            time_hours = f"'{categorize_time_hours(row['TIME (HOURS)'])}'"
            dogs = row['DOGS']
            cars = row['4X4']
            season = row['SEASON']
            region = row['REGION']

            elevation_gain_m = elevation_gain_m.replace(',', '.')

            f.write(
                "INSERT INTO hikings VALUES ("
                f"'{hike_name}', '{ranking}', '{difficulty}', {distance_km}, {elevation_gain_m}, '{gradient}', {time_hours}, '{dogs}', '{cars}', '{season}', '{region}'"
                ");\n"
            )

        f.close()


