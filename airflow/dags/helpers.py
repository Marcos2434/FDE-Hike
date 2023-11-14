import praw
import json

reddit_credentials = praw.Reddit(
    client_id="FmDPjXlF33v45zALJvQuEg",
    client_secret="-8egIOAFeqweAASt_NRUjVxPke5dyw",
    user_agent="hiking-app por u/Asteteh",
)

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
        publicacion_principal = {
            "Title": post.title,
            "Upvotes": post.score,
            "Comments": []
        }

        post.comments.replace_more(limit=None)

        for comment in post.comments.list():
            if hasattr(comment, 'author'):
                datos_comentario = {
                    "Content": comment.body,
                    "Upvotes": comment.score
                }
                publicacion_principal["Comments"].append(datos_comentario)

        top_posts.append(publicacion_principal)

    # Order the main posts by upvotes in descending order
    top_posts.sort(key=lambda x: x["Upvotes"], reverse=True)

    # Capture the top 5 posts
    publicaciones = top_posts[:5]

    # Serialize the results in JSON format
    json_result = json.dumps(publicaciones, indent=4, ensure_ascii=False)

    with open("posts.json", "w", encoding="utf-8") as f: f.write(json_result)


