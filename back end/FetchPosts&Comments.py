import os
import praw
import logging
import argparse
from prawcore import session
import requests
import pandas as pd
from datetime import date, timezone, timedelta, datetime
from dotenv import load_dotenv, find_dotenv
from typing import List, Dict, Optional
from praw.models import Submission
from sqlalchemy import String

SESSION_CONFIG = {
    "FP1": {
        "keywords": ["fp1", "free practice 1", "practice 1"],
    },
    "FP2": {
        "keywords": ["fp2", "free practice 2", "practice 2"],
    },
    "FP3": {
        "keywords": ["fp3", "free practice 3", "practice 3"],
    },
    "SPRINT QUALIFYING": {
        "keywords": ["sprint qualifying", "sprint shootout", "sprint quali", "sprint q"],
    },
    "SPRINT": {
        "keywords": ["sprint", "sprint race"],
    }, 
    "QUALIFYING": {
        "keywords": ["quali", "qualifying", "q1", "q2", "q3"],
    },
    "RACE": {
        "keywords": ["race", "grand prix", "gp", "race thread", "race discussion"],
    }
}
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
            year = year or date.today().year
            if round is not None:
                url = f"https://api.jolpi.ca/ergast/f1/{year}/{round}.json"
            else:
                url = f"https://api.jolpi.ca/ergast/f1/{year}/last.json"
            
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
                "Races" : data
            }
            print(f"DEBUG: Race info found: {race_info}")
            print(f"DEBUG: Available session keys: {[k for k in data.keys() if k in ['FirstPractice', 'SecondPractice', 'ThirdPractice', 'Sprint', 'SprintQualifying', 'Qualifying', 'Race']]}")
            return race_info
            
        except requests.RequestException as e:
            logging.error(f"Error fetching race info: {e}")
            raise
        except (KeyError, IndexError) as e:
            logging.error(f"Error parsing race data: {e}")
            print(f"DEBUG: Full API response: {resp.text}")
            raise

    def IsSprintWeekend(self, race_data: dict) -> bool:
        """
        Determines if race weekend is a sprint weekend
        """
        if 'Sprint' in race_data or 'SprintQualifying' in race_data:
            print("DEBUG: Found 'Sprint' / 'SprintQualifying' in race_data")
            print("Sprint Weekend!")
            return True

        print("DEBUG: Normal Weekend!")
        return False

def ValidateEnvVars() -> None:
    """Validates the required env variables"""
    requiredVars = ["CLIENT_ID", "CLIENT_SECRET", "USER_AGENT"]
    missingVars = [var for var in requiredVars if not os.getenv(var)]
    if missingVars:
        raise ValueError(f"Missing required environment variables: {missingVars}")

def CreateFileName(raceName: str, session: str, year: int) -> str:
    """Creates a file name from race name & session"""
    safeName = raceName.replace(" ", "_").replace("'", "").lower()
    return f"f1_{year}_{safeName}_{session.lower()}_reddit.csv"

def GetSessionDates(race_data: dict) -> dict:
    """
    Extracts session dynamically from the API response
    """
    session_dates = {}

    print(f"DEBUG: Extracting session dates from race data")
    print(f"DEBUG: Top-level keys: {list(race_data.keys())}")

    session_objects = ['FP1', 'FP2', 'FP3', 'Qualifying', 'Race', 'Sprint', 'SprintQualifying']
    for session in session_objects:
        if session in race_data:
            session_data = race_data[session]
            if isinstance(session_data, dict) and 'date' in session_data:
                session_dates[session] = session_data['date']
                print(f"DEBUG: Found {session} on {session_data['date']}")

    if 'Sessions' in race_data:
        sessions = race_data['Sessions']
        if isinstance(sessions, list):
            session_type = session.get('type', 'Unknown')
            session_date = session.get('date')
            if session_date:
                session_dates[session_type] = session_date
                print(f"Fount {session_type} on session_date")

    if 'Sprint' in race_data:
        sprint_data = race_data['Sprint']
        if isinstance(sprint_data, dict) and 'date' in sprint_data:
            session_dates['Sprint'] = sprint_data['date']
            print(f"DEBUG: Found Sprint on {sprint_data['date']}")
    
    if 'SprintQualifying' in race_data:
        sprint_qual_data = race_data['SprintQualifying']
        if isinstance(sprint_qual_data, dict) and 'date' in sprint_qual_data:
            session_dates['Sprint Qualifying'] = sprint_qual_data['date']
            print(f"DEBUG: Found Sprint Qualifying on {sprint_qual_data['date']}")

    print(f"DEBUG: Final session dates: {session_dates}")
    return session_dates

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

    scraper = RedditScraper(
        client_id=os.getenv("CLIENT_ID"),
        client_secret=os.getenv("CLIENT_SECRET"),
        user_agent=os.getenv("USER_AGENT")
    )

    race_data = scraper.GetRaceInfo(2025, 6)
    session_dates = GetSessionDates(race_data)

    """
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
        sub = scraper.reddit.subreddit(args.subreddit)
        scraper.IsSprintWeekend(raceInfo)

        session_upper = args.session.upper()
        if session_upper not in SESSION_CONFIG:
            raise ValueError(f"Invalid session type: {args.session}. Valid options are: {list(SESSION_CONFIG.keys())}")
        
        keywords = SESSION_CONFIG[session_upper]['keywords']
        offset_days = SESSION_CONFIG[session_upper]['offset_days']

        race_date = datetime.strptime(raceInfo["date"], "%Y-%m-%d")
        session_start = (race_date + timedelta(days=offset_days)).replace(tzinfo=timezone.utc)
        session_end = session_start + timedelta(days=1)
        start_epoch = int(session_start.timestamp())
        end_epoch = int(session_end.timestamp())
        
        print(f"DEBUG: Race date: {race_date}")
        print(f"DEBUG: Session date range: {session_start} to {session_end}")
        print(f"DEBUG: Epoch range: {start_epoch} to {end_epoch}")
        print(f"DEBUG: Keywords: {keywords}")

        records = []
        posts_checked = 0
        posts_in_date_range = 0
        posts_matched = 0
        
        race_name_clean = raceInfo["race_name"].replace("Grand Prix", "").strip()
        search_queries = [
            f'"{raceInfo["race_name"]}"',
            f'"{race_name_clean}"',
            f'"{raceInfo["race_name"]}" {args.session.lower()}',
            f'{race_name_clean} {args.session.lower()}'
        ]
        
        for query in search_queries:
            print(f"DEBUG: Searching with query: {query}")
            try:
                for post in sub.search(query, time_filter="all", sort="top", limit=args.post_limit):
                    posts_checked += 1
                    post_time = post.created_utc
                    post_datetime = datetime.fromtimestamp(post_time, tz=timezone.utc)
                    
                    print(f"DEBUG: Post {posts_checked}: '{post.title[:60]}...' created at {post_datetime}")
                    
                    if start_epoch <= post_time <= end_epoch:
                        posts_in_date_range += 1
                        print(f"DEBUG: Post {posts_checked} is in date range")
                        
                        title_lower = post.title.lower()
                        if any(kw in title_lower for kw in keywords):
                            posts_matched += 1
                            print(f"DEBUG: Post {posts_checked} matches keywords, processing...")
                            
                            rec = ProcessPost(post, args.session, args.comment_limit)
                            if rec:
                                records.append(rec["posts"])
                                records.extend(rec["comments"])
                                print(f"DEBUG: Added {1 + len(rec['comments'])} records from post {posts_checked}")
                        else:
                            print(f"DEBUG: Post {posts_checked} doesn't match keywords: {title_lower}")
                    else:
                        print(f"DEBUG: Post {posts_checked} outside date range")
                        
            except Exception as e:
                print(f"DEBUG: Error searching with query '{query}': {e}")
                continue
        
        if posts_matched < 5:
            print(f"DEBUG: Only found {posts_matched} posts via search, trying recent posts...")
            try:
                for post in sub.new(limit=1000):  # Check more recent posts
                    posts_checked += 1
                    post_time = post.created_utc
                    
                    if post_time < start_epoch - 86400 * 7:  # Stop if more than a week before
                        break
                        
                    if start_epoch <= post_time <= end_epoch:
                        posts_in_date_range += 1
                        title_lower = post.title.lower()
                        
                        # More flexible matching for race names
                        race_name_parts = race_name_clean.lower().split()
                        if (any(kw in title_lower for kw in keywords) and 
                            (any(part in title_lower for part in race_name_parts) or 
                             raceInfo["race_name"].lower() in title_lower)):
                            
                            posts_matched += 1
                            print(f"DEBUG: Found matching post via new(): '{post.title[:60]}...'")
                            
                            rec = ProcessPost(post, args.session, args.comment_limit)
                            if rec:
                                records.append(rec["posts"])
                                records.extend(rec["comments"])
                                
            except Exception as e:
                print(f"DEBUG: Error browsing new posts: {e}")

        print(f"DEBUG: Search Summary:")
        print(f"  - Total posts checked: {posts_checked}")
        print(f"  - Posts in date range: {posts_in_date_range}")
        print(f"  - Posts matched keywords: {posts_matched}")
        print(f"  - Total records collected: {len(records)}")

        if not records:
            print("WARNING: No records found. Creating empty CSV file.")
            df = pd.DataFrame(columns=[
                "id", "session", "title", "selftext", "score", "created", 
                "permalink", "author", "num_comments", "type"
            ])
        else:
            df = pd.DataFrame(records)
        
        filename = CreateFileName(raceInfo["race_name"], args.session, int(raceInfo["year"]))
        df.to_csv(filename, index=False)

        logging.info(f"Successfully wrote {len(df)} records to {filename}")
        print(f"DEBUG: File {filename} created with {len(df)} records")
        
    except Exception as e:
        logging.error(f"Error in main: {e}")
        print(f"DEBUG: Exception details: {type(e).__name__}: {e}")
        raise
    """

if __name__ == "__main__":
    main()