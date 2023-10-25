# pip install spacy
# python -m spacy download en_core_web_sm

import spacy
from collections import Counter
import praw  # Python Reddit API Wrapper

# Initialize spaCy with the English language model
nlp = spacy.load("en_core_web_sm")

# Reddit API credentials
reddit = praw.Reddit(
    client_id="YOUR_CLIENT_ID",
    client_secret="YOUR_CLIENT_SECRET",
    user_agent="YOUR_USER_AGENT",
)

# Function to extract keywords from Reddit text
def extract_keywords(text, num_keywords=5):
    doc = nlp(text)
    nouns = [token.text for token in doc if token.pos_ == "NOUN"]
    adjectives = [token.text for token in doc if token.pos_ == "ADJ"]
    keywords = nouns + adjectives
    keyword_freq = Counter(keywords)
    top_keywords = keyword_freq.most_common(num_keywords)
    return top_keywords

# Specify the Reddit post you want to analyze
post_url = "https://www.reddit.com/r/learnpython/comments/abc123/my_reddit_post_url"

submission = reddit.submission(url=post_url)

# Extract keywords from the post title
title_keywords = extract_keywords(submission.title, num_keywords=5)
print("Title Keywords:")
for keyword, freq in title_keywords:
    print(f"{keyword}: {freq}")

# Extract keywords from the post body text
body_keywords = extract_keywords(submission.selftext, num_keywords=5)
print("\nBody Keywords:")
for keyword, freq in body_keywords:
    print(f"{keyword}: {freq}")
