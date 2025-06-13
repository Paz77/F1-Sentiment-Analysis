import os
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
            
            print(f"DEBUG: Fetching race info from: {url}")
            resp = requests.get(url)
            resp.raise_for_status()
            
            json_data = resp.json()
            print(f"DEBUG: API Response keys: {json_data.keys()}")
            
            races = json_data["MRData"]["RaceTable"]["Races"]
            if not races:
                raise ValueError(f"No race data found for year {year}, round {round}")
            
            data = races[0]
            race_info = {
                "race_name" : data["raceName"],
                "circuit_name" : data["Circuit"]["circuitName"],
                "date" : data["date"]
            }
            print(f"DEBUG: Race info found: {race_info}")
            return race_info
            
        except requests.RequestException as e:
            logging.error(f"Error fetching race info: {e}")
            raise
        except (KeyError, IndexError) as e:
            logging.error(f"Error parsing race data: {e}")
            print(f"DEBUG: Full API response: {resp.text}")
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
        raise ValueError(f"Missing required environment variables: {missingVars}")

def CreateFileName(raceName: str, session: str) -> str:
    """Creates a file name from race name & session"""
    safeName = raceName.replace(" ", "_").lower()
    return f"f1_{safeName}_{session.lower()}_reddit.csv"

def ProcessPost(post: Submission, session: str, comment_limit: int) -> Optional[Dict]:
    """
    Processes a Reddit post and its comments.
    Args:
        post: Reddit Submission object
        session: Session type
        comment_limit: Maximum number of comments to fetch
        
    Returns:
        Dictionary containing post and comment data
    """
    try:
        post.comments.replace_more(limit=0)
        comments = post.comments.list()[:comment_limit]

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
            "type": "post"
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
                "session": session,
                "type": "comment"  
            })
        
        return {"posts": postData, "comments": commentData}
        
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
        print(f"DEBUG: Starting scraper with args: {args}")
        
        scraper = RedditScraper(
            client_id=os.getenv("CLIENT_ID"),
            client_secret=os.getenv("CLIENT_SECRET"),
            user_agent=os.getenv("USER_AGENT")
        )

        raceInfo = scraper.GetRaceInfo(args.year, args.round)
        raceDatetime = datetime.fromisoformat(raceInfo["date"]).replace(tzinfo=timezone.utc)
        endDatetime = raceDatetime + timedelta(days=7)
        startDateTime = raceDatetime - timedelta(days=2)
        
        print(f"DEBUG: Race date range: {raceDatetime} to {endDatetime}")

        keywords = SessionKeywords.GetKeywords(args.session)
        if not keywords:
            raise ValueError(f"Invalid session type: {args.session}")

        start_epoch = int(startDateTime.timestamp())
        end_epoch = int(endDatetime.timestamp())

        query = (f'timestamp{start_epoch}..{end_epoch}'
                 f'"{raceInfo["race_name"]}"'
                 f'({" OR ".join(keywords)})')
        print(f"DEBUG: Search query: {query}")
        
        sub = scraper.reddit.subreddit(args.subreddit)
        print(f"DEBUG: Searching subreddit: {args.subreddit}")

        records = []
        posts_found = 0
        posts_in_date_range = 0
        posts_processed = 0
        
        for post in sub.search(query, syntax="cloudsearch", sort="new", limit=args.post_limit * 2):
            posts_found += 1
            record_time = datetime.fromtimestamp(post.created_utc, tz=timezone.utc)
            
            print(f"DEBUG: Post {posts_found}: '{post.title}' created at {record_time}")
            
            posts_in_date_range += 1
            print(f"DEBUG: Post {posts_found} is in date range, processing...")
            
            result = ProcessPost(post, args.session, args.comment_limit)
            if result:
                posts_processed += 1
                records.append(result["posts"])
                records.extend(result["comments"])
                print(f"DEBUG: Added {1 + len(result['comments'])} records from post {posts_found}")

        print(f"DEBUG: Summary:")
        print(f"  - Total posts found: {posts_found}")
        print(f"  - Posts in date range: {posts_in_date_range}")
        print(f"  - Posts successfully processed: {posts_processed}")
        print(f"  - Total records to write: {len(records)}")

        if not records:
            print("WARNING: No records found. Creating empty CSV file.")
            df = pd.DataFrame(columns=[
                "id", "session", "title", "selftext", "score", "created", 
                "permalink", "author", "num_comments", "type"
            ])
        else:
            df = pd.DataFrame(records)
        
        filename = CreateFileName(raceInfo["race_name"], args.session)
        df.to_csv(filename, index=False)

        logging.info(f"Successfully wrote {len(df)} records to {filename}")
        print(f"DEBUG: File {filename} created with {len(df)} records")
        
    except Exception as e:
        logging.error(f"Error in main: {e}")
        print(f"DEBUG: Exception details: {type(e).__name__}: {e}")
        raise

if __name__ == "__main__":
    main()