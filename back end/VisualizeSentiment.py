import argparse
import logging
import pandas as pd
import matplotlib.pyplot as plt
from database import F1Database
from datetime import datetime

def visualize_sentiment(db: F1Database, year: int, round_num: int, session: str):
    if session:

def main():
    parser = argparse.ArgumentParser(description="Visualize sentiment for f1 reddit posts")
    parser.add_argument("--year", type=int, default=datetime.now().year, help="F1 season year (default: current year)")
    parser.add_argument("--round", type=int, required=True, help="F1 race round number")
    parser.add_argument("--session", choices=["FP1", "FP2", "FP3", "Sprint Qualifying", "Sprint", "Qualifying", "Race"], help="Specific session to visualize (optional)")
    args = parser.parse_args()

    db = F1Database()
    try:

    


if __name__ == "__main__":
    main()