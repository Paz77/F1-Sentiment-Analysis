import argparse
import logging
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import alpha
from database import F1Database
from datetime import datetime

def visualize_sentiment_histogram(db: F1Database, year: int, round_num: int, session: str):
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

def visualize_sentiment_timeline(db: F1Database, year: int, round_num: int, session: str):
    """Creates a line graph to show average sentiment over time"""
    try:
        data = db.get_sentiment(session, round_num, year)
        if not data:
            print(f"Sentiment data not found for {session}, Round {round_num}, {year}")
            return

        df = pd.DataFrame(data)
        df['created_at'] = pd.to_datetime(df['created_at'])
        df = df.sort_values('created_at')
        df_clean = df.dropna(subset=['vader_score'])

        if len(df_clean) == 0:
            print("No valid sentiment scores found")
            return

        df_clean['hour'] = df_clean['created_at'].dt.floor('H')
        hourly_avg = df_clean.groupby('hour')['vader_score'].agg(['mean', 'count']).reset_index()

        plt.figure(figsize=(12, 6))
        
        plt.plot(hourly_avg['hour'], hourly_avg['mean'], marker='o', linewidth=2, markersize=6, 
                color='blue', label='Average Sentiment')
        
        plt.axhline(y=0, color='red', linestyle='--', alpha=0.5, label='Neutral Sentiment')
        
        if len(hourly_avg) > 1:
            hourly_stats = df_clean.groupby('hour')['vader_score'].agg(['mean', 'count', 'std']).reset_index()
            
            plt.fill_between(hourly_stats['hour'], 
                            hourly_stats['mean'] - hourly_stats['std'],
                            hourly_stats['mean'] + hourly_stats['std'],
                            alpha=0.2, color='blue', label='±1 Std Dev')

        plt.xlabel('Time')
        plt.ylabel('Average Sentiment Score (VADER)')
        plt.title(f'Average Sentiment Over Time - {session}, Round {round_num}, {year}')
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.xticks(rotation=45)

        overall_mean = df_clean['vader_score'].mean()
        trend_text = f'Overall Average: {overall_mean:.3f}\nTime Points: {len(hourly_avg)}\nTotal Posts: {len(df_clean)}'
        plt.text(0.02, 0.98, trend_text, transform=plt.gca().transAxes, 
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
        
        plt.tight_layout()
        plt.show()

        print(f"\nTimeline Analysis for {session}, Round {round_num}, {year}:")
        print(f"Time range: {df_clean['created_at'].min()} to {df_clean['created_at'].max()}")
        print(f"Overall average sentiment: {overall_mean:.3f}")
        print(f"Number of time intervals: {len(hourly_avg)}")
        print(f"Sentiment trend: {'Positive' if overall_mean > 0 else 'Negative' if overall_mean < 0 else 'Neutral'}")
    
    except Exception as e:
        logging.error(f"Error creating timeline visualization: {e}")
        print(f"Error: {e}")

def main():
    parser = argparse.ArgumentParser(description="Visualize sentiment for f1 reddit posts")
    parser.add_argument("--year", type=int, default=datetime.now().year, help="F1 season year (default: current year)")
    parser.add_argument("--round", type=int, required=True, help="F1 race round number")
    parser.add_argument("--session", choices=["FP1", "FP2", "FP3", "Sprint Qualifying", "Sprint", "Qualifying", "Race"], help="Specific session to visualize (optional)")
    args = parser.parse_args()

    db = F1Database()
    try:
        visualize_sentiment_histogram(db, args.year, args.round, args.session)
        visualize_sentiment_timeline(db, args.year, args.round, args.session)

    except Exception as e:
        logging.error(f"Error in main: {e}")
        print(f"Error: {e}")

if __name__ == "__main__":
    main()