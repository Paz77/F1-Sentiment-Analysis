import os
import praw
import logging
import argparse
import requests
import pandas as pd
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv, find_dotenv

sessionKeywords = {
    "FP1" : ["fp1", "free practice 1"],
    "FP2" : ["fp2", "free practice 2"],
    "FP3" : ["fp3", "free practice 3"],
    "Qualifying" : ["quali", "qualifying"],
    "Race" : ["race", "grand prix", "gp", "race thread"]
}

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
parser.add_argument("--session", type=str, default="Race", help="FP1, FP2, FP3, Qualifying, Race")
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

selectedKeywords = sessionKeywords.get(args.session, [])
query = " OR ".join(selectedKeywords)
posts = sub.search(query, time_filter="week", sort="top", limit=args.post_limit)

for post in posts:
    try:
        post.comments.replace_more(limit=0)
        comments = post.comments.list()[: args.comment_limit]
        records.append({
            "id": post.id,
            "session" : args.session,
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

safeRaceName = race_name.replace(" ", "_")
fileName = f"f1_{safeRaceName.lower()}_{args.session.lower()}_reddit.csv"

df = pd.DataFrame(records)
df.to_csv(fileName, index=False)

logging.info(f"Wrote {len(df)} records to {fileName}")