import argparse
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import alpha
from database import F1Database
from datetime import datetime

def visualize_sentiment(db: F1Database, year: int, round_num: int, session: str):
    try:
        data = db.get_sentiment(session, round_num, year)
        if not data:
            print(f"No sentiment data found for {session}, Round {round_num}, {year}")
            return
        
        df = pd.DataFrame(data)
        
        sentiment_scores = df['vader_score'].dropna()
        if len(sentiment_scores) == 0:
            print("No valid sentiment scores found")
            return

        plt.figure(figsize=(10, 6))
        plt.hist(sentiment_scores, bins=20, edgecolor='black', alpha=0.7, color='skyblue')
        plt.xlabel('Sentiment Score (aka vader)')
        plt.ylabel('Frequency (Num of Posts & Comments)')
        plt.title(f'Sentiment Distribution - Year: {year}, Round: {round_num}, Session: {session}')
        plt.grid(True, alpha=0.3)

        mean = sentiment_scores.mean()
        median = sentiment_scores.median()
        std = sentiment_scores.std()

        stats_text = f'Mean: {mean:.3f}\nMedian: {median:.3f}\nStd Dev: {std:.3f}\nCount: {len(sentiment_scores)}'
        plt.text(0.02, 0.98, stats_text, transform=plt.gca().transAxes, 
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        plt.tight_layout()
        plt.show()

        print(f"\nSentiment Analysis Summary for {session}, Round {round_num}, {year}:")
        print(f"Total posts/comments analyzed: {len(sentiment_scores)}")
        print(f"Average sentiment: {mean:.3f}")
        print(f"Median sentiment: {median:.3f}")
        print(f"Standard deviation: {std:.3f}")
        print(f"Most negative score: {sentiment_scores.min():.3f}")
        print(f"Most positive score: {sentiment_scores.max():.3f}")
    
    except Exception as e:
        logging.error(f"Error creating visualization: {e}")
        print(f"Error: {e}")

        

def main():
    parser = argparse.ArgumentParser(description="Visualize sentiment for f1 reddit posts")
    parser.add_argument("--year", type=int, default=datetime.now().year, help="F1 season year (default: current year)")
    parser.add_argument("--round", type=int, required=True, help="F1 race round number")
    parser.add_argument("--session", choices=["FP1", "FP2", "FP3", "Sprint Qualifying", "Sprint", "Qualifying", "Race"], help="Specific session to visualize (optional)")
    args = parser.parse_args()

    db = F1Database()
    try:
        visualize_sentiment(db, args.year, args.round, args.session)

    except Exception as e:
        logging.error(f"Error in main: {e}")
        print(f"Error: {e}")

if __name__ == "__main__":
    main()