import os
import praw
import logging
import argparse
import requests
import pandas as pd
from database import F1Database
from datetime import date, timezone, timedelta, datetime
from dotenv import load_dotenv, find_dotenv
from typing import List, Dict, Optional
from praw.models import Submission

SESSION_CONFIG = {
    "FP1": {
        "keywords": ["fp1", "free practice 1", "practice 1", "fp1 discussion", "fp1 thread", "fp1 results", "fp1 live"],
    },
    "FP2": {
        "keywords": ["fp2", "free practice 2", "practice 2", "fp2 discussion", "fp2 thread", "fp2 results", "fp2 live"],
    },
    "FP3": {
        "keywords": ["fp3", "free practice 3", "practice 3", "fp3 discussion", "fp3 thread", "fp3 results", "fp3 live"],
    },
    "SPRINT QUALIFYING": {
        "keywords": [
            "sprint qualifying", "sprint shootout", "sprint quali", "sprint q",
            "sprint qualifying discussion", "sprint qualifying thread", "sprint shootout discussion", 
            "sprint shootout thread", "sq discussion", "sq thread", "sprint qualifying results",
            "sprint shootout results", "sprint qualifying live", "sprint shootout live"
        ],
    },
    "SPRINT": {
        "keywords": [
            "sprint", "sprint race", "sprint discussion", "sprint thread", "sprint race discussion",
            "sprint race thread", "sprint results", "sprint race results", "sprint live", "sprint race live",
            "sprint session", "sprint race session", "sprint start", "sprint race start"
        ],
    }, 
    "QUALIFYING": {
        "keywords": ["quali", "qualifying", "q1", "q2", "q3", "qualifying discussion", "qualifying thread", "quali discussion", "quali thread", "qualifying results", "quali results", "qualifying live", "quali live"],
    },
    "RACE": {
        "keywords": ["race", "grand prix", "gp", "race thread", "race discussion", "race results", "race live", "race start", "race finish", "race podium", "race highlights", "race recap", "race analysis", "race review"],
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
    
def GetRaceInfo(year: Optional[int] = None, round: Optional[int] = None) -> Dict:
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

def ValidateEnvVars() -> None:
    """Validates the required env variables"""
    requiredVars = ["CLIENT_ID", "CLIENT_SECRET", "USER_AGENT"]
    missingVars = [var for var in requiredVars if not os.getenv(var)]
    if missingVars:
        raise ValueError(f"Missing required environment variables: {missingVars}")

def CreateFileName(round_num: int, race_name: str, session: str, year: int) -> str:
    """Creates a file name from race name & session"""
    safeName = race_name.replace(" ", "_").replace("'", "").lower()
    return f"f1_{year}_round_{round_num}_{safeName}_{session.lower()}_reddit.csv"

def GetSessionDates(race_data: dict) -> dict:
    """
    Extracts session dynamically from the API response
    """
    session_dates = {}

    print(f"DEBUG: Extracting session dates from race data")
    print(f"DEBUG: Top-level keys: {list(race_data.keys())}")

    sessions = ['DATE', 'FIRSTPRACTICE', 'SECONDPRACTICE', 'THIRDPRACTICE', 'SPRINTQUALIFYING', 'SPRINT', 'QUALIFYING'] #date == actual race on sunday
    for key, val in race_data.items():
        if key.upper() in sessions:
            if isinstance(val, str): 
                session_dates[key] = val
                print(f"DEBUG: Found top-level {key} on {val}")
            elif isinstance(val, dict) and 'date' in val: 
                session_dates[key] = val['date']
                print(f"DEBUG: Found top-level {key} on {val['date']}")

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
            try:
                commentData.append({
                    "id": getattr(comment, 'id', None),
                    "link_id": getattr(comment, 'link_id', None),
                    "parent_id": getattr(comment, 'parent_id', None),
                    "body": getattr(comment, 'body', ''),
                    "score": getattr(comment, 'score', 0),
                    "created": datetime.fromtimestamp(getattr(comment, 'created_utc', 0)).isoformat(),
                    "author": getattr(comment.author, "name", None) if comment.author else None,
                    "session": session,
                    "type": "comment"  
                })
            except Exception as e:
                logging.warning(f"Error processing comment {getattr(comment, 'id', 'unknown')}: {e}")
                continue 
        
        return {"posts": postData, "comments": commentData}
        
    except Exception as e:
        logging.warning(f"Error processing post {post.id}: {e}")
        return None

def GetSessionWindow(session_type: str, session_date: datetime) -> tuple:
    """
    Returns <start, end> times for specific session
    """
    if session_type in ["FP1", "FP2", "FP3"]:
        start = session_date - timedelta(days=2)
        end = session_date + timedelta(days=1)
    elif session_type in ["QUALIFYING", "SPRINT QUALIFYING"]:
        start = session_date - timedelta(days=1)
        end = session_date + timedelta(days=1)
    elif session_type == "SPRINT":
        start = session_date - timedelta(days=1)
        end = session_date + timedelta(days=1)
    elif session_type == "RACE":
        start = session_date - timedelta(days=1)
        end = session_date + timedelta(days=2)
    else:
        start = session_date - timedelta(days=1)
        end = session_date + timedelta(days=1)
    
    return start.replace(tzinfo=timezone.utc), end.replace(tzinfo=timezone.utc)

def ValidateSessionExists(session_type: str, session_dates: dict) -> bool:
    """
    Validates if the requested session exists for this race weekend.
    
    Args:
        session_type: The session type (FP1, FP2, etc.)
        session_dates: Dictionary of available session dates from API
        
    Returns:
        True if session exists, False otherwise
    """
    session_mapping = {
        "FP1": "FirstPractice",
        "FP2": "SecondPractice", 
        "FP3": "ThirdPractice",
        "QUALIFYING": "Qualifying",
        "SPRINT": "Sprint",
        "SPRINT QUALIFYING": "SprintQualifying",
        "RACE": "date"  
    }
    
    if session_type not in session_mapping:
        return False
        
    session_key = session_mapping[session_type]
    return session_key in session_dates

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
    parser.add_argument("--session", type=str, default="Race", help="Session type (FP1, FP2, FP3, SprintQualifying, Sprint, Qualifying, Race)")
    parser.add_argument("--year", type=int, default=None, help="Year of the race")
    parser.add_argument("--round", type=int, default=None, help="Round number of the race")
    parser.add_argument("--export_csv", action="store_true", help="export results to csv")
    args = parser.parse_args()

    try:
        print(f"DEBUG: Starting scraper with args: {args}")
        
        db = F1Database()

        scraper = RedditScraper(
            client_id=os.getenv("CLIENT_ID"),
            client_secret=os.getenv("CLIENT_SECRET"),
            user_agent=os.getenv("USER_AGENT")
        )
                
        race_info = GetRaceInfo(args.year, args.round)
        race_data = race_info["Races"]  
        db.insert_race(race_data)
        
        session_dates = GetSessionDates(race_data)        
        sub = scraper.reddit.subreddit(args.subreddit)

        session_upper = args.session.upper()
        if session_upper not in SESSION_CONFIG:
            raise ValueError(f"Invalid session type: {args.session}. Valid options are: {list(SESSION_CONFIG.keys())}")
        
        if not ValidateSessionExists(session_upper, session_dates):
            available_sessions = [k for k in session_dates.keys() if k != 'date']
            raise ValueError(
                f"Session '{args.session}' does not exist for this race weekend. "
                f"Available sessions: {available_sessions}"
            )
        
        keywords = SESSION_CONFIG[session_upper]['keywords']
        
        race_date = datetime.strptime(race_data["date"], "%Y-%m-%d")
        
        session_date_key = None
        if args.session.upper() == "FP1":
            session_date_key = "FirstPractice"
        elif args.session.upper() == "FP2":
            session_date_key = "SecondPractice"
        elif args.session.upper() == "FP3":
            session_date_key = "ThirdPractice"
        elif args.session.upper() == "QUALIFYING":
            session_date_key = "Qualifying"
        elif args.session.upper() == "SPRINT":
            session_date_key = "Sprint"
        elif args.session.upper() == "SPRINT QUALIFYING":
            session_date_key = "SprintQualifying"
        elif args.session.upper() == "RACE":
            session_date_key = "date"

        if session_date_key and session_date_key in session_dates:
            session_date = datetime.strptime(session_dates[session_date_key], "%Y-%m-%d")
            session_start, session_end = GetSessionWindow(args.session.upper(), session_date)
        else:
            print(f"WARNING: Session date not found for {args.session}, using race date as fallback")
            session_start, session_end = GetSessionWindow(args.session.upper(), race_date)
        
        start_epoch = int(session_start.timestamp())
        end_epoch = int(session_end.timestamp())
        
        print(f"DEBUG: Race date: {race_date}")
        print(f"DEBUG: Session date range: {session_start} to {session_end}")
        print(f"DEBUG: Epoch range: {start_epoch} to {end_epoch}")
        print(f"DEBUG: Keywords: {keywords}")

        posts_checked = 0
        posts_in_date_range = 0
        posts_matched = 0
        posts_inserted = 0
        comments_inserted = 0
        
        race_name_clean = race_data["raceName"].replace("Grand Prix", "").strip()
        search_queries = [
            f'"{race_data["raceName"]}"',
            f'"{race_name_clean}"',
            f'"{race_data["raceName"]}" {args.session.lower()}',
            f'{race_name_clean} {args.session.lower()}',
            f'"{args.session.upper()}"', 
            f'"{args.session.upper()} discussion"',  
            f'"{args.session.upper()} thread"', 
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
                                print(f"DEBUG: Attempting to insert post {rec['posts']['id']}")
                                
                                post_success = db.insert_post(rec["posts"], race_data)
                                if post_success:
                                    posts_inserted += 1
                                    print(f"DEBUG: Successfully inserted post {rec['posts']['id']}")
                                else:
                                    print(f"DEBUG: Failed to insert post {rec['posts']['id']}")
                                
                                comment_success_count = 0
                                for comment in rec["comments"]:
                                    comment_success = db.insert_comment(comment, rec["posts"]["id"], race_data)
                                    if comment_success:
                                        comments_inserted += 1
                                        comment_success_count += 1
                                
                                print(f"DEBUG: Inserted {comment_success_count}/{len(rec['comments'])} comments for post {rec['posts']['id']}")
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
                for post in sub.new(limit=1000): 
                    posts_checked += 1
                    post_time = post.created_utc
                    
                    if post_time < start_epoch - 86400 * 7: 
                        break
                        
                    if start_epoch <= post_time <= end_epoch:
                        posts_in_date_range += 1
                        title_lower = post.title.lower()
                        
                        race_name_parts = race_name_clean.lower().split()
                        if (any(kw in title_lower for kw in keywords) and 
                            (any(part in title_lower for part in race_name_parts) or 
                             race_data["raceName"].lower() in title_lower)):
                            
                            posts_matched += 1
                            print(f"DEBUG: Found matching post via new(): '{post.title[:60]}...'")
                            
                            rec = ProcessPost(post, args.session, args.comment_limit)
                            if rec:
                                print(f"DEBUG: Attempting to insert post {rec['posts']['id']}")
                                
                                post_success = db.insert_post(rec["posts"], race_data)
                                if post_success:
                                    posts_inserted += 1
                                    print(f"DEBUG: Successfully inserted post {rec['posts']['id']}")
                                else:
                                    print(f"DEBUG: Failed to insert post {rec['posts']['id']}")
                                
                                comment_success_count = 0
                                for comment in rec["comments"]:
                                    comment_success = db.insert_comment(comment, rec["posts"]["id"], race_data)
                                    if comment_success:
                                        comments_inserted += 1
                                        comment_success_count += 1
                                
                                print(f"DEBUG: Inserted {comment_success_count}/{len(rec['comments'])} comments for post {rec['posts']['id']}")
                        else:
                            print(f"DEBUG: Post {posts_checked} doesn't match keywords: {title_lower}")
                    else:
                        print(f"DEBUG: Post {posts_checked} outside date range")
                        
            except Exception as e:
                print(f"DEBUG: Error browsing new posts: {e}")

        print(f"DEBUG: Search Summary:")
        print(f"  - Total posts checked: {posts_checked}")
        print(f"  - Posts in date range: {posts_in_date_range}")
        print(f"  - Posts matched keywords: {posts_matched}")
        print(f"  - Posts inserted: {posts_inserted}")
        print(f"  - Comments inserted: {comments_inserted}")

        if not posts_inserted:
            raise ValueError(f"No Reddit posts found for {args.session} session of {race_data['raceName']} ({race_data['season']} Round {race_data['round']})")
        
        if args.export_csv:
            filename = CreateFileName(
                round_num=int(race_data["round"]),
                race_name=race_data["raceName"],
                session=args.session,
                year=int(race_data["season"])
            )
            db.export_to_csv(args.session, race_data["round"], race_data["season"], filename)
            logging.info(f"Exported data to {filename}")
        else:
            logging.info(f"Successfully inserted {posts_inserted} posts and {comments_inserted} comments into database")
        
    except Exception as e:
        logging.error(f"Error in main: {e}")
        print(f"DEBUG: Exception details: {type(e).__name__}: {e}")
        raise

if __name__ == "__main__":
    main()