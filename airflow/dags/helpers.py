import praw
import json
import os
import csv

import redis
import random

import spacy
from collections import Counter

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
