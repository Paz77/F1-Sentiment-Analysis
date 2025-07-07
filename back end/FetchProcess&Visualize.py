import os
import sys
import time
import json
import logging
import requests
import argparse
import subprocess
from datetime import datetime, date
from urllib import request, response
from typing import List, Dict, Optional

class F1BatchScraper:
    def __init__(self, script_path: str = "back end/FetchPosts&Comments.py", process_script_path: str = "back end/ProcessText.py"):
        self.script_path = script_path
        self.process_script_path = process_script_path
        self.sessions = ["Race"]
    
    def get_completed_races(self, year: int) -> List[Dict]:
        """
        Fetches all completed races for a given year & returns a list of dictionaries of race info
        """
        try:
            url = f"https://api.jolpi.ca/ergast/f1/{year}.json"
            print(f"fetching data from: {url}")

            response = requests.get(url)
            response.raise_for_status()

            data = response.json()
            races = data["MRData"]["RaceTable"]["Races"]

            current_date = datetime.now().date()
            completed_races = []
            
            for race in races:
                race_date = datetime.strptime(race["date"], "%Y-%m-%d").date()
                
                if race_date <= current_date:
                    race_info = {
                        "round" : int(race["round"]),
                        "race_name" : race["raceName"],
                        "circuit_name" : race["Circuit"]["circuitName"],
                        "date" : race["date"],
                        "year" : year
                    }
                    completed_races.append(race_info)

            print(f"Found {len(completed_races)} completed races")
            return completed_races
        
        except requests.RequestException as e:
            print(f"Error fetching race calendar: {e}")
            return []
        
        except (KeyError, IndexError, ValueError) as e:
            print(f"Error parsing race data: {e}")
            return []
        
    def execute_scraper(self, year: int, round_num: int, session: str, **kwargs) -> bool:
        """
        Runs FetchPosts&Comments.py with the given parameters
        Returns true if successful, else false
        """
        try:
            cmd = [
                "python", self.script_path, 
                "--year", str(year), 
                "--round", str(round_num),
                "--session", session
            ]

            for key, value in kwargs.items():
                if value is not None:
                    cmd.extend([f"--{key}", str(value)])

            print(f"Running: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode==0:
                print(f"Successfully scraped {year} Round {round_num} & {session}")
                if result.stdout:
                    for line in result.stdout.split('\n'):
                        if 'Successfully wrote' in line or 'records to' in line:
                            print(f"{line}")

                if kwargs.get('process_sentiment', True):
                    print(f"Processing sentiment for {year} Round {round_num} {session}...")
                    self.execute_processor(year, round_num, session)
                
                return True
            else:
                print(f"Failed to scrape {year} Round {round_num} & {session}")
                if result.stderr:
                    print(f"Error: {result.stderr.strip()}")
                return False
        
        except subprocess.TimeoutExpired:
            print(f"Timeout scraping {year} Round {round_num} & {session}")
            return False

        except Exception as e:
            print(f"Exception scraping {year} Round {round_num} & {session}")
            return False
        
    def scrape_all_races(self, year: int, sessions: Optional[List[str]] = None, start_round: int = 1, end_round: Optional[int] = None, **scraper_params) ->Dict[str, int]:
        """
        Scrapes all races for given year
        """
        completed_races = self.get_completed_races(year)
        stats = {"total": 0, "successful": 0, "failed": 0}

        if not completed_races:
            print(f"No completed races found for {year}")
            return stats
        
        if end_round:
            completed_races = [r for r in completed_races if start_round <= r["round"] <= end_round]
        else:
            completed_races = [r for r in completed_races if r["round"] >= start_round]
        
        print(f"Starting batch scrape for {len(completed_races)} races")
        print("=" * 60)

        for race in completed_races:
            race_round = race["round"]
            race_name = race["race_name"]
            
            race_sessions = get_sessions_for_race(year, race_round, sessions)
            
            if not race_sessions:
                print(f"No valid sessions found for {year} Round {race_round} ({race_name})")
                continue
            
            print(f"Processing round {race_round}: {race_name} ({race['date']})")
            print(f"  Sessions to scrape: {', '.join(race_sessions)}")
            
            for session in race_sessions:
                stats["total"] += 1
                
                success = self.execute_scraper(
                    year=year,
                    round_num=race_round,
                    session=session, 
                    **scraper_params
                )
                if success:
                    stats["successful"] += 1
                else:
                    stats["failed"] += 1
            print() 
        
        return stats
    
    def scrape_specific_race(self, race_configs: List[Dict], **scraper_params) -> Dict[str, int]:
        """
        Scrapes specific race & respective session
        """
        stats = {"total": 0, "successful": 0, "failed": 0}

        print(f"Now targeting scrape for {len(race_configs)} race/session combinations")
        print("=" * 60)

        for config in race_configs:
            year = config["year"]
            round_num = config["round"]
            session = config["session"]

            stats["total"] += 1
            print(f"Processing {year} Round {round_num} {session}")

            sucess = self.execute_scraper(
                year=year,
                round_num=round_num,
                session=session, 
                **scraper_params
            )

            if sucess:
                stats["successful"] += 1
            else:
                stats["failed"] += 1
            
            time.sleep(2)

        return stats

    def execute_processor(self, year: int, round_num: int, session: Optional[str] = None) -> bool:
        """Runs ProcessText.py with given parameters & returns true if successful, else false :3"""
        try: 
            cmd = [
                "python", self.process_script_path,
                "--year", str(year),
                "--round", str(round_num)
            ]

            if session:
                cmd.extend(["--session", session])

            print(f"Running processor: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )

            if(result.returncode == 0):
                print(f"Successfully processed sentiment for {year} Round {round_num} {session or 'all sessions'}")
                if result.stdout:
                    for line in result.stdout.split('\n'):
                        if 'Results saved to' in line or 'Processing batch' in line:
                            print(f"  {line}")
                return True
            else:
                print(f"Failed to process sentiment for {year} Round {round_num} {session or 'all sessions'}")
                if result.stderr:
                    print(f"Error: {result.stderr.strip()}")
                return False
        
        except subprocess.TimeoutExpired:
            print(f"Timeout processing sentiment for {year} Round {round_num} {session or 'all sessions'}")
            return False

        except Exception as e:
            print(f"Exception processing sentiment for {year} Round {round_num} {session or 'all sessions'}: {e}")
            return False

def IsSprintWeekend(year: int, race_round) -> bool:
    """detects if a race round is a sprint weekend"""
    try:
        url = f"https://api.jolpi.ca/ergast/f1/{year}/{race_round}.json"
        print(f"Checking sprint status for {year} Round {race_round}: {url}")

        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        races = data["MRData"]["RaceTable"]["Races"]
        if not races:
            print(f"No races found for {year} Round {race_round}")
            return False

        race = races[0];
        race_json_str = json.dumps(race, indent=2).lower()

        sprint_terms = ["sprint", "sprint qualifying"]
        has_sprint = any(term in race_json_str for term in sprint_terms)
        
        if has_sprint:
            print(f"{year} Round {race_round} ({race.get('raceName', 'Unknown')}) is a SPRINT weekend")
        else:
            print(f"{year} Round {race_round} ({race.get('raceName', 'Unknown')}) is a standard weekend")
        
        return has_sprint
    
    except requests.RequestException as e:
        print(f"Error fetching race data for {year} Round {race_round}: {e}")
        return False
    except (KeyError, IndexError, ValueError) as e:
        print(f"Error parsing race data for {year} Round {race_round}: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error checking sprint status for {year} Round {race_round}: {e}")
        return False

def get_sessions_for_race(year: int, race_round: int, user_sessions: Optional[List[str]] = None) -> List[str]:
    """
    Gets the appropriate sessions for a specific race round.
    If user_sessions is provided, filters it based on weekend type.
    """
    is_sprint = IsSprintWeekend(year, race_round)
    available_sessions = []

    if is_sprint:
        available_sessions = ["FP1", "Sprint Qualifying", "Sprint", "Qualifying", "Race"]
        print(f"Sprint weekend detected - available sessions: {', '.join(available_sessions)}")
    else:
        available_sessions = ["FP1", "FP2", "FP3", "Qualifying", "Race"]
        print(f"Standard weekend detected - available sessions: {', '.join(available_sessions)}")

    if user_sessions:
        valid_sessions = [session for session in user_sessions if session in available_sessions]
        
        invalid_sessions = [session for session in user_sessions if session not in available_sessions]
        if invalid_sessions:
            print(f"Skipping invalid sessions for this weekend type: {', '.join(invalid_sessions)}")
        
        return valid_sessions
    
    return available_sessions
        
def main():
    all_sessions = ["FP1", "FP2", "FP3", "Sprint Qualifying", "Sprint", "Qualifying", "Race"]
    
    parser = argparse.ArgumentParser(description="Batch Scrape F1 reddit posts & comments")
    parser.add_argument("--mode", choices=["all", "year", "specific"], default="year", help="Scraping mode: all completed races, specific year, or specific configs")
    parser.add_argument("--year", type=int, default=2025, help="Year to scrape (default: 2025)")
    parser.add_argument("--start_round", type=int, default=1, help="Starting round number (default: 1)")
    parser.add_argument("--end_round", type=int, default=None, help="Ending round number (default: all completed)")
    parser.add_argument("--sessions", nargs="+", choices=all_sessions, default=None, help="Sessions to scrape (default: auto-detect based on weekend type)")
    parser.add_argument("--script_path", default="back end/FetchPosts&Comments.py", help="Path to FetchPosts&Comments.py script")
    parser.add_argument("--subreddit", default="formula1", help="subreddit to scrape")
    parser.add_argument("--post_limit", type=int, default=200, help="Post limit per session")
    parser.add_argument("--comment_limit", type=int, default=25, help="Comment limit per post")
    parser.add_argument("--config", type=str, default=None, help="JSON string of specific race configs (for specific mode)")
    parser.add_argument("--no_sentiment", action="store_true", help="Skip sentiment processing")

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    scraper = F1BatchScraper(args.script_path)

    scraper_params = {
        "subreddit": args.subreddit,
        "post_limit": args.post_limit,
        "comment_limit": args.comment_limit
    }
    
    try:
        if args.mode == "all":
            curr_year = date.today().year
            total_stats = {"total" : 0, "successful" : 0, "failed" : 0}

            for year in range(2020, curr_year + 1):
                print({f"Processing year {year}"})

                year_stats = scraper.scrape_all_races(
                    year=year,
                    sessions=args.sessions,  
                    **scraper_params
                )
                for key in total_stats:
                    total_stats[key] += year_stats[key]

            stats = total_stats    

        elif args.mode == "year":
            stats = scraper.scrape_all_races(
                year=args.year,
                sessions=args.sessions,
                start_round=args.start_round,
                end_round=args.end_round,
                **scraper_params
            )

        elif args.mode == "specific":
            if not args.config:
                print("Error: --config required for specific mode")
                print("Example: --config '[{\"year\":2025,\"round\":1,\"session\":\"Race\"}]'")
                sys.exit(1)

            race_configs = json.loads(args.config)
            stats = scraper.scrape_specific_race(race_configs, **scraper_params)

        print("\n" + "=" * 60)
        print("FINAL SUMMARY")
        print("=" * 60)
        print(f"Total scraping attempts: {stats['total']}")
        print(f"Successful: {stats['successful']}")
        print(f"Failed: {stats['failed']}")
        print(f"Success rate: {(stats['successful']/stats['total']*100):.1f}%" if stats['total'] > 0 else "0%")

    except KeyboardInterrupt:
        print("\nScraping interrupted by user")
    except Exception as e:
        print(f"\nError during batch scraping: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()