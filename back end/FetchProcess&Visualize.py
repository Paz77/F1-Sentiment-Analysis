import os
import sys
import subprocess
import requests
import argparse
import json
import logging
from datetime import datetime, date
from typing import List, Dict, Optional
import time

class F1BatchScraper:
    def __init__(self, script_path: str = "back end/FetchPosts&Comments.py"):
        self.script_path = script_path
    
    def get_completed_races(self, year: int) -> List[Dict]:
        """
        Fetches all completed races for a given year & returns a list of dictionaries of race info
        """
        try:
            url = f"https://api.jolpi.ca/ergast/f1/{year}.json"

            response = requests.get(url)
            response.raise_for_status()

            data = response.json()
            races = data["MRData"]["RaceTable"]["Races"]

            current_date = datetime.now().date()
            comepleted_races = []
            
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
                    comepleted_races.append(race_info)

            return comepleted_races
        
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
        if sessions is None:
            sessions = self.sessions

        completed_races = self.get_completed_races(year)
        stats = {"total": 0, "successful": 0, "failed": 0}

        if not completed_races:
            print(f"No comepleted races found for {year}")
            return stats
        
        if end_round:
            completed_races = [r for r in completed_races if start_round <= r["round"] <= end_round]
        else:
            completed_races = [r for r in completed_races if r["round"] >= start_round]
        
        print(f"Starting batch scrape for {len(completed_races)} races, {len(sessions)} sessions each")
        print(f"Sessions: {', '.join(sessions)}")
        print("=" * 60)

        for race in completed_races:
            race_round = race["round"]
            race_name = race["race_name"]

            print(f"Processing round {race_round}: {race_name} ({race["date"]})")
            for session in sessions:
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
            stats["failed"] -= 1

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
        
def main():
    parser = argparse.ArgumentParser(description="Batch Scrape F1 reddit posts & comments")
    parser.add_argument("--mode", choices=["all", "year", "specific"], default="year", help="Scraping mode: all completed races, specific year, or specific configs")

    parser.add_argument("--year", type=int, default=2025, help="Year to scrape (default: 2025)")
    parser.add_argument("--start_round", type=int, default=1, help="Starting round number (default: 1)")
    parser.add_argument("--end_round", type=int, default=None, help="Ending round number (default: all completed)")

    parser.add_argument("--sessions", nargs="+", choices=["FP1", "FP2", "FP3", "Qualifying", "Race"], default="Race", help="Sessions to scrape (default: Race only)")

    parser.add_argument("--script_path", default="back end/FetchPosts&Comments.py", help="Path to FetchPosts&Comments.py script")
    parser.add_argument("--subreddit", default="formula1", help="subreddit to scrape")
    parser.add_argument("--post_limit", type=int, default=50, help="Post limit per session")
    parser.add_argument("--comment_limit", type=int, default=10, help="Comment limit per post")

    parser.add_argument("--config", type=str, default=None, help="JSON string of specific race configs (for specific mode)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    scraper = F1BatchScraper(args.script_path)

    scraper_params = {
        "subreddit" : args.subreddit,
        "post_limit" : args.post_limit,
        "comment_limit" : args.comment_limit
    }
    
    try:
        if args.mode == "all":
            curr_year = date.today().year
            total_stats = {"total" : 0, "successful" : 0, "failed" : 0}

            for year in range(2020, curr_year + 1):
                print({f"Processing year {year}"})

                year_stats = scraper.scrape_all_races(
                    year=year,
                    sessions=args.session,
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
            if not args.configs:
                print("Error: --configs required for specific mode")
                print("Example: --configs '[{\"year\":2025,\"round\":1,\"session\":\"Race\"}]'")
                sys.exit(1)

            race_configs = json.loads(args.configs)
            stats = scraper.scrape_specific_races(race_configs, **scraper_params)

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