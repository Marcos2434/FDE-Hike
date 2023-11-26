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
from transformers import pipeline



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
mongo_collection_hikes = mongo_db['hikes']

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
        
        # removed redis for ingestion
        # redis_client.set('extract_hiking', json_data)
        
        
        # save only 5 first hikes
        json_data = json.dumps(table_data[:40], ensure_ascii=False, indent=2)
        with open(os.path.join(DATA_DIR, 'data_hiking.json'), 'w') as json_file:
            json_file.write(json_data)

    else:
        print(f"Error: {response.status_code}")

# support function, responsible for transforming the data
def categorize_time_hours(time_hours):
    if '0 - 2' in time_hours or '2 - 4' in time_hours:
        return 'Short'
    elif '4 - 6' in time_hours or '6 - 8' in time_hours:
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

def transformation_redis_hikes(hike_key):

    data = redis_client.get(hike_key)
    hike_data_list = json.loads(data)

    for hike_data in hike_data_list:
        hike_data['TIME (HOURS)'] = categorize_time_hours(hike_data['TIME (HOURS)'])
        hike_data['RANKING'] = categorize_stars(hike_data['RANKING'])
        hike_data['ELEVATION GAIN (M)'] = hike_data['ELEVATION GAIN (M)'].replace(',', '.')

    redis_client.set(hike_key, json.dumps(hike_data_list))

def insert_mongo():
    with open(os.path.join(DATA_DIR, 'data_hiking.json'), 'r') as json_file:
        hike_data_list = json.load(json_file)
    
    name_collection = 'hikes'
    if name_collection in mongo_db.list_collection_names():
        mongo_collection = mongo_db[name_collection]
        mongo_collection.drop()

    mongo_collection_hikes.insert_many(hike_data_list)

def check_internet_connection(**kwargs):
    try:
        requests.get("http://www.google.com", timeout=5)
        return kwargs['online_task']
    except requests.ConnectionError:
        return kwargs['offline_task']

def extract_hikes_data_offline():
    pass
    # with open(os.path.join(DATA_DIR, 'data_hiking.json'), 'r') as json_file:
    #     data = json.load(json_file)
    #     redis_client.set('extract_hiking', json.dumps(data))

def insert_data_mongo_in_neo4j():
    # Delete all existing nodes and relationships in the Neo4j database
    graph.delete_all()

    # Recover data from MongoDB
    data = mongo_collection_hikes.find({}, {'_id': 0, 'HIKE NAME': 1, 'RANKING': 1, 'DIFFICULTY': 1, 'TIME (HOURS)': 1, 'REGION': 1})

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

    data = mongo_collection_hikes.find({}, {'_id': 0, 'HIKE NAME': 1})
    hike_names = [hike_data['HIKE NAME'] for hike_data in data]

    
    # Save title, content, comments, upvotes and downvotes for each hike posts
    all_hikes_posts = {}
    for hike_name in hike_names:
        subreddit = reddit_credentials.subreddit(subreddit_name)
        search_results = subreddit.search(hike_name, limit=limit)

        top_posts = []

        for post in search_results:
            top_post = {
                "title": post.title,
                "content": post.selftext,
                "upvotes": post.ups,
                "downvotes": post.downs,
                "comments": []
            }

            # limit to first 10 comments
            
            for comment in post.comments:
                top_post["comments"].append({
                    "Content": comment.body,
                    "Upvotes": comment.ups,
                    "Downvotes": comment.downs
                })

            top_posts.append(top_post)

        # Order the main posts by upvotes in descending order
        top_posts.sort(key=lambda x: x["upvotes"], reverse=True)

        # Capture the top 5 posts
        posts = top_posts[:5]
        
        all_hikes_posts[hike_name] = posts
    

    json_data = json.dumps(all_hikes_posts, indent=4, ensure_ascii=False)
    with open(os.path.join(DATA_DIR, 'all_hikes_posts.json'), 'w') as json_file:
        json_file.write(json_data)


def natural_language_processing():
    # Load the keywords from csv files in the keywords directory
    topics = {}
    for root, dirs, files in os.walk(KEYWORDS_DIR):
        for file in files:
            if file.endswith(".csv"):
                with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                    filename = file.split(".")[0]
                    topics[filename] = [word.strip() for word in next(csv.reader(f))]

    nlp = spacy.load('en_core_web_sm')

    # Dictionary to store results
    all_hikes_keywords = {}
    
    # Load Reddit info
    with open(os.path.join(DATA_DIR, 'all_hikes_posts.json'), 'r') as json_file:
        all_hikes_posts = json.load(json_file)

    # Create dictionary keys
    for hike_name, _ in all_hikes_posts.items(): 
        all_hikes_keywords[hike_name] = {}
    
    
    # Download the BERT model using transformers
    bert_model = "nlptown/bert-base-multilingual-uncased-sentiment"
    nlp_sentiment = pipeline('sentiment-analysis', model=bert_model)
    
    topic_sentiment_list = {}
    # Perform NLP and sentiment analysis for each hike
    for hike_name, posts in all_hikes_posts.items():
        topic_sentiment_list[hike_name] = {}
        for topic_name, keyword_list in topics.items():
            keyword_counter = Counter()
            sentiment_counter = {}
            
            total_sentiment_of_topic = 0
            number_of_posts = len(posts)
            
            topic_comment_sentiment = {
                "hike_name": hike_name,
                "topic_name": topic_name,
            }
            
            # Count keywords in each post
            for post in posts:

                # from content
                doc = nlp(post["content"])

                for token in doc:
                    if not token.is_stop and not token.is_punct:
                        lemma = token.lemma_
                        if lemma in keyword_list:
                            keyword_counter[lemma] += 1
                            
                # content sentiment
                if post["content"]:
                    sentiment = nlp_sentiment(post["content"])[0]
                    total_sentiment_of_topic += sentiment['score']
                else:
                    number_of_posts -= 1 # if no content, don't count it
                
                    
                
                # from comments
                for comment in post["comments"]:
                    # nlp for keywords
                    doc = nlp(comment["Content"])
                    for token in doc:
                        if not token.is_stop and not token.is_punct:
                            lemma = token.lemma_
                            if lemma in keyword_list:
                                keyword_counter[lemma] += 1
                                
                                # sentiment analysis for comment
                                comment_sentiment = nlp_sentiment(comment["Content"])[0]
                                
                                try:
                                    sentiment_counter[lemma]['positive_sentiment'] += 1
                                except KeyError:
                                    sentiment_counter[lemma] = {
                                        "positive_sentiment": 0,
                                        "negative_sentiment": 0,
                                        "neutral_sentiment": 0
                                    }
                                
                                if comment_sentiment['score'] > 0.25: sentiment_counter[lemma]['positive_sentiment'] += 1
                                elif comment_sentiment['score'] < 0.25: sentiment_counter[lemma]['negative_sentiment'] += 1
                                else: sentiment_counter[lemma]['neutral_sentiment'] += 1
                                

                    
            overall_content_sentiment_for_topic = total_sentiment_of_topic / number_of_posts if number_of_posts > 0 else 0
            print(overall_content_sentiment_for_topic)
            topic_sentiment_list[hike_name][topic_name] = {
                "overall_content_sentiment_for_topic":
                        'positive_sentiment' if overall_content_sentiment_for_topic > 0.25 
                        else 'negative_sentiment' if overall_content_sentiment_for_topic < -0.25 
                        else 'neutral_sentiment'
            }


            # Get the 10 most frequent keywords in all posts
            top_keywords = keyword_counter.most_common(10)

            
            # Create a list of the top keywords
            top_keywords_and_sentiment_list = [{
                "word": word, 
                "count": count,
            } for word, count in top_keywords]
            
            # for word, count in top_keywords:
            #     print(word)
            
            
            comment_sentiment_list = [sentiment_counter[word] for word, _ in top_keywords if word in sentiment_counter.keys()]

            
            # Add the list to the dictionary
            all_hikes_keywords[hike_name][topic_name] = top_keywords_and_sentiment_list
    

    # Serialize the dictionary in JSON format
    json_result = json.dumps(all_hikes_keywords, indent=4, ensure_ascii=False)

    # Save the results in a single JSON file for all hikes
    output_file_path = os.path.join(DATA_DIR, "all_hikes_keywords.json")
    with open(output_file_path, "w", encoding="utf-8") as f:
        f.write(json_result)
        
    comment_sentiment_list_json = json.dumps(comment_sentiment_list, indent=4, ensure_ascii=False)
    output_file_path = os.path.join(DATA_DIR, "comment_sentiment_list.json")
    with open(output_file_path, "w", encoding="utf-8") as f:
        f.write(comment_sentiment_list_json)
        
    topic_sentiment_list_json = json.dumps(topic_sentiment_list, indent=4, ensure_ascii=False)
    output_file_path = os.path.join(DATA_DIR, "topic_sentiment_list.json")
    with open(output_file_path, "w", encoding="utf-8") as f:
        f.write(topic_sentiment_list_json)
    


# def determine_popularity():
#     with open(os.path.join(DATA_DIR, 'all_hikes_posts.json'), 'r') as json_file:
#         all_hikes_posts = json.load(json_file)
    
#     for post in all_hikes_posts:
    

def add_topics_neo4j():
    """
    Loops over all hikes and adds, via the NLP computed data, the topics to the neo4j database, creating nodes and relationships.
    Where one hike will have connecting nodes in such a way that if you query a hike for "nature" you will get all the nature keywords.
    """
    
    with open(os.path.join(DATA_DIR, 'all_hikes_keywords.json'), 'r') as json_file:
        all_hikes_keywords = json.load(json_file)
        
    with open(os.path.join(DATA_DIR, 'topic_sentiment_list.json'), 'r') as json_file:
        topic_sentiment_list = json.load(json_file)
    
    for hike_name, topics in all_hikes_keywords.items():
        hike_node = Node("Hike", name=hike_name)
        graph.merge(hike_node, "Hike", "name")

        for topic_name, keywords in topics.items():
            for keyword in keywords:
                keyword_node = Node("Keyword", name=keyword['word'], count=keyword['count'], content_sentiment=topic_sentiment_list[hike_name][topic_name]['overall_content_sentiment_for_topic'])
                
                graph.merge(keyword_node, "Keyword", "name")

                relation_keyword = Relationship(hike_node, f'{topic_name}', keyword_node)
                graph.create(relation_keyword)
    
# legacy: postgres
def _insert():
    df = pd.read_json('data/data_hiking.json')
    with open("/opt/airflow/dags/inserts.sql", "w") as f:
        f.write(
            "DROP TABLE IF EXISTS hikes;\n"
            "CREATE TABLE IF NOT EXISTS hikes (\n"
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
                "INSERT INTO hikes VALUES ("
                f"'{hike_name}', '{ranking}', '{difficulty}', {distance_km}, {elevation_gain_m}, '{gradient}', {time_hours}, '{dogs}', '{cars}', '{season}', '{region}'"
                ");\n"
            )

        f.close()


