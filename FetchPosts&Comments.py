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

for post in subreddit.hot(limit = 10):
    print(f"{post.title} [{post.score} votes]")