import os
import argparse
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv, find_dotenv
import praw
import pandas as pd
import requests
from datetime import datetime, timedelta

load_dotenv(find_dotenv())
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

resp = requests.get("https://api.jolpi.ca/ergast/f1/current/next.json")
data = resp.json()["MRData"]["RaceTable"]["Races"][0]

race_name     = data["raceName"]             
circuit_name  = data["Circuit"]["circuitName"]
race_date     = data["date"]                 
race_datetime = datetime.fromisoformat(race_date)
end_datetime  = race_datetime + timedelta(days=3)

parser = argparse.ArgumentParser()
parser.add_argument("--subreddit", default="formula1")
parser.add_argument("--post_limit", type=int, default=50)
parser.add_argument("--comment_limit", type=int, default=10)
parser.add_argument("--output", default=race_name + ".csv")
args = parser.parse_args()

reddit = praw.Reddit(
    client_id=os.getenv("CLIENT_ID"),
    client_secret=os.getenv("CLIENT_SECRET"),
    user_agent=os.getenv("USER_AGENT")
)

records = []

sub = reddit.subreddit(args.subreddit)

start_dt = race_datetime.replace(tzinfo=timezone.utc)
end_dt   = end_datetime.  replace(tzinfo=timezone.utc)
start_ts = start_dt.timestamp()
end_ts   = end_dt.timestamp()

posts = (
    p for p in sub.new(limit=args.post_limit)
    if race_name.lower()    in p.title.lower()
    or circuit_name.lower() in p.title.lower()
    or (start_ts <= p.created_utc <= end_ts)
)

for post in posts:
    try:
        post.comments.replace_more(limit=0)
        comments = post.comments.list()[: args.comment_limit]
        records.append({
            "id": post.id,
            "title": post.title,
            "selftext": post.selftext,
            "score": post.score,
            "created": datetime.fromtimestamp(post.created_utc).isoformat(),
            "permalink": post.permalink,
            "author": getattr(post.author, "name", None),
            "num_comments": post.num_comments,
        })
        for c in comments:
            records.append({
                "id": c.id,
                "link_id": c.link_id,
                "parent_id": c.parent_id,
                "body": c.body,
                "score": c.score,
                "created": datetime.fromtimestamp(c.created_utc).isoformat(),
                "author": getattr(c.author, "name", None),
            })
    except Exception as e:
        logging.warning(f"Skipping post {post.id} due to error: {e}")

df = pd.DataFrame(records)
df.to_csv(args.output, index=False)
logging.info(f"Wrote {len(df)} records to {args.output}")