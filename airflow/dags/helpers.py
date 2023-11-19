import praw
import json
import os
import csv
import requests
import pandas as pd

import redis
import random
import pymongo as py

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

myclient = py.MongoClient("mongodb://mongo:27017/")
mongo_db = myclient['hiking_db']
mongo_collection_hikings = mongo_db['hikings']




def call_reddit_api(hike_name, limit, subreddit_name='all'):
    """Calls reddit api to get the top <limit> posts of a given hike.

    Args:
        hike_name (string): name of the hike to search for.
        limit (int): number of posts to return.
        subreddit_name (str, optional): name of subreddit to look in. Defaults to 'all'.
    """
        
    subreddit = reddit_credentials.subreddit("all")
    search_results = subreddit.search(hike_name, limit=limit)

    top_posts = []

    for post in search_results:
        top_post = {
            "Title": post.title,
            "Upvotes": post.score,
            "Comments": []
        }

        post.comments.replace_more(limit=None)

        for comment in post.comments.list():
            if hasattr(comment, 'author'):
                comment_details = {
                    "Content": comment.body,
                    "Upvotes": comment.score
                }
                top_post["Comments"].append(comment_details)

        top_posts.append(top_post)

    # Order the main posts by upvotes in descending order
    top_posts.sort(key=lambda x: x["Upvotes"], reverse=True)

    # Capture the top 5 posts
    posts = top_posts[:5]

    # Serialize the results in JSON format
    posts_json = json.dumps(posts, indent=4, ensure_ascii=False)

    # save post info in redis
    redis_client.hset(f'hike:{hike_name}', 'Hikes', posts_json)


    

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

    
    # Peform NLP on all comments in post
    for key, value in keywords.items():
        keyword_counter = Counter()

        # Loop over hikes
        for hike_key in redis_client.keys('hike*'):
            
            # Loop over the posts in the hike and perform NLP
            # hike_name = hike_key.split(":")[1]
            hike_data = redis_client.hgetall(hike_key)
            posts = json.loads(hike_data["Hikes"])
            for post in posts:
                for comment in post["Comments"]:
                    text_to_analyze = comment["Content"]
                    doc = nlp(text_to_analyze)
                    
                    for token in doc:
                        if not token.is_stop and not token.is_punct:
                            lemma = token.lemma_
                            if lemma in value:
                                keyword_counter[lemma] += 1

        # Get the 10 most frequent keywords in the post
        top_keywords = keyword_counter.most_common(10)

        print("The 10 most frequent words are:")
        for keyword, count in top_keywords:
            print(f"{keyword}: {count}")
        
        # Serialize the results in JSON format
        json_result = json.dumps(top_keywords, indent=4, ensure_ascii=False)
        output_file_path = os.path.join(BASE_DIR, f"data/{key}.json")
        with open(output_file_path, "w", encoding="utf-8") as f: 
            f.write(json_result)


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

def categorize_time_hours(time_hours):
    if '0 – 2' in time_hours or '2 – 4' in time_hours:
        return 'Short'
    elif '4 – 6' in time_hours or '6 – 8' in time_hours:
        return 'Medium'
    else:
        return 'Long'

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

    for document in mongo_collection_hikings.find():
        print(document)

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


