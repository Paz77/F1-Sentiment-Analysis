import os
from dotenv import find_dotenv, load_dotenv

dotenv_path = find_dotenv()
load_dotenv(dotenv_path)

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
USER_AGENT =os.getenv("USER_AGENT")

import praw, pandas as pd

reddit = praw.Reddit(
    client_id = CLIENT_ID,
    client_secret = CLIENT_SECRET,
    user_agent = USER_AGENT
)

subreddit = reddit.subreddit("formula1")

records = []

for post in subreddit.hot(limit = 1):
    records.append({
        "id" : post.id,
        "title" : post.title,
        "selftext" : post.selftext,
        "score": post.score,
        "created": post.created_utc
    })
    post.comments.replace_more(limit = 300)
    for c in post.comments[:10]:
        records.append({
            "id" : c.id,
            "parent_id" : post.id,
            "body" : c.body,
            "score": c.score,
            "created": c.created_utc
        })
 
df = pd.DataFrame(records)
df.to_csv("f1_reddit.csv", index=False)