import os
import sys
import subprocess
import requests
import argparse
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
                race_date = race.datetime.strptime(race["date"], "%Y-%m-%d").date()
                
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
