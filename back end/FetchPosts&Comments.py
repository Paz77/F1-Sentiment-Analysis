from ast import Dict
import os
from pandas.core.computation.ops import Op
import praw
import logging
import argparse
import requests
import pandas as pd
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv, find_dotenv
from typing import List, Dict, Optional
from praw.models import Submission

class RedditScraper:
    def __init__(self, client_id: str, client_secret: str, user_agent: str):
        """
        Initializes reddit scraper w/ authentication
        """
        self.reddit = praw.Reddit(
            client_id = client_id,
            client_secret = client_secret,
            user_agent = user_agent
        )
    
    def GetRaceInfo(self, year: Optional[int] = None, round: Optional[int] = None) -> Dict:
        """
        Fetch race info from Ergast API.
        Args:
            year: optionally add which f1 year
            round: optionally add which f1 race 
        Returns:
            Dictionary containing race information
        """
        try:
            if year is not None and round is not None:
                url = f"https://api.jolpi.ca/ergast/f1/{year}/{round}.json"
            elif year is not None:
                url = f"https://api.jolpi.ca/ergast/f1/{year}/last.json"
            else:
                url = "https://api.jolpi.ca/ergast/f1/current/next.json"
                
            resp = requests.get(url)
            resp.raise_for_status()
            data = resp.json()["MRData"]["RaceTable"]["Races"][0]
            return {
                "race_name" : data["raceName"],
                "circuit_name" : data["Circuit"]["circuitName"],
                "date" : data["date"]
            }
        except requests.RequestException as e:
            logging.error(f"Error fetching race info: {e}")
            raise

class SessionKeywords:
    SESSION_MAP = {
        "FP1": ["fp1", "free practice 1"],
        "FP2": ["fp2", "free practice 2"],
        "FP3": ["fp3", "free practice 3"],
        "QUALIFYING": ["quali", "qualifying"],
        "RACE": ["race", "grand prix", "gp", "race thread"]
    }

    @classmethod
    def GetKeywords(cls, session: str) -> List[str]:
        """
        Gets keywords for a certain session, i.e., fp1, quali, grand prix
        Args:
            session: Session type (FP1, FP2, FP3, Qualifying, Race)
        Returns:
            List of keywords for the session
        """
        session = session.upper()
        keywords = cls.SESSION_MAP.get(session, [])
        if not keywords:
            logging.warning(f"No keywords found for session type: {session}")
        return keywords

def ValidateEnvVars() -> None:
    """Validates the required env variables"""
    requiredVars = ["CLIENT_ID", "CLIENT_SECRET", "USER_AGENT"]
    missingVars = [var for var in requiredVars if not os.getenv(var)]
    if missingVars:
        raise ValueError(f"Missing required environtment variable")

def CreateFileName(raceName: str, session: str) -> str:
    """Creates a file name from race name & session"""
    safeName = raceName.replace(" ", "_").lower();
    return f"f1_{safeName}_{session.lower()}_reddit.csv"

def ProcessPost(post: Submission, session: str) -> Dict:
    """
    Processes a Reddit post and its comments.
    Args:
        post: Reddit Submission object
        session: Session type
        
    Returns:
        Dictionary containing post and comment data
    """
    try:
        post.comments.replace_more(limit=0)
        comments = post.comments.list()

        postData = {
            "id": post.id,
            "session": session,
            "title": post.title,
            "selftext": post.selftext,
            "score": post.score,
            "created": datetime.fromtimestamp(post.created_utc).isoformat(),
            "permalink": post.permalink,
            "author": getattr(post.author, "name", None),
            "num_comments": post.num_comments,
        }
        commentData = []
        for comment in comments:
            commentData.append({
                "id": comment.id,
                "link_id": comment.link_id,
                "parent_id": comment.parent_id,
                "body": comment.body,
                "score": comment.score,
                "created": datetime.fromtimestamp(comment.created_utc).isoformat(),
                "author": getattr(comment.author, "name", None),
            })
        return {"posts" : postData, "comments" : commentData}
    except Exception as e:
        logging.warning(f"Error processing post {post.id}: {e}")
        return None

def main():
    load_dotenv(find_dotenv())
    ValidateEnvVars()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s"
    )

    parser = argparse.ArgumentParser(description="Fetch Reddit posts and comments for F1 sessions")
    parser.add_argument("--subreddit", default="formula1", help="Subreddit to search")
    parser.add_argument("--post_limit", type=int, default=50, help="Maximum number of posts to fetch")
    parser.add_argument("--comment_limit", type=int, default=10, help="Maximum number of comments per post")
    parser.add_argument("--session", type=str, default="Race", help="Session type (FP1, FP2, FP3, Qualifying, Race)")
    parser.add_argument("--year", type=int, default=None, help="Year of the race")
    parser.add_argument("--round", type=int, default=None, help="Round number of the race")
    args = parser.parse_args()

    try:
        scraper = RedditScraper(
            client_id=os.getenv("CLIENT_ID"),
            client_secret=os.getenv("CLIENT_SECRET"),
            user_agent=os.getenv("USER_AGENT")
        )

        raceInfo = scraper.GetRaceInfo(args.year, args.round)
        raceDatetime = datetime.fromisoformat(raceInfo["date"])
        endDatetime = raceDatetime + timedelta(days=3)

        keywords = SessionKeywords.GetKeywords(args.session)
        if not keywords:
            raise ValueError(f"Invalid session type: {args.session}")

        query = " OR ".join(keywords)
        sub = scraper.reddit.subreddit(args.subreddit)

        records = []
        for post in sub.search(query, time_filter="week", sort="top", limit=args.post_limit):
            result = ProcessPost(post, args.session)
            if result:
                records.append(result["posts"])
                records.extend(result["comments"][:args.comment_limit])

        df = pd.DataFrame(records)
        filename = CreateFileName(raceInfo["race_name"], args.session)
        df.to_csv(filename, index=False)

        logging.info(f"Successfully wrote {len(df)} records to {filename}")
    except Exception as e:
        logging.error(f"Error in main: {e}")
        raise

if __name__ == "__main__":
    main()