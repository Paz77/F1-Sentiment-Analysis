import argparse
import logging
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import alpha
from database import F1Database
from datetime import datetime
import io  

def visualize_sentiment_histogram(db: F1Database, year: int, round_num: int, session: str, save_to_db: bool = True):
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

        plt.figure(figsize=(12, 7))
        
        # Create histogram with color coding
        n, bins, patches = plt.hist(sentiment_scores, bins=20, edgecolor='black', alpha=0.7)
        
        # Color code the bars based on sentiment
        for i, (patch, bin_center) in enumerate(zip(patches, (bins[:-1] + bins[1:]) / 2)):
            if bin_center < 0:
                patch.set_facecolor('red')  # Negative sentiment
                patch.set_alpha(0.6)
            elif bin_center > 0:
                patch.set_facecolor('green')  # Positive sentiment
                patch.set_alpha(0.6)
            else:
                patch.set_facecolor('gray')  # Neutral sentiment
                patch.set_alpha(0.4)
        
        # Add vertical line at 0 to separate positive/negative
        plt.axvline(x=0, color='black', linestyle='--', linewidth=2, alpha=0.8, label='Neutral (0)')
        
        plt.xlabel('Sentiment Score (VADER)')
        plt.ylabel('Frequency (Number of Posts & Comments)')
        plt.title(f'Sentiment Distribution - {session}, Round {round_num}, {year}')
        plt.grid(True, alpha=0.3)

        # Add text labels for positive/negative regions
        plt.text(0.7, 0.95, 'POSITIVE', transform=plt.gca().transAxes, 
                fontsize=14, fontweight='bold', color='green', ha='center',
                bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.8))
        plt.text(0.3, 0.95, 'NEGATIVE', transform=plt.gca().transAxes, 
                fontsize=14, fontweight='bold', color='red', ha='center',
                bbox=dict(boxstyle='round', facecolor='lightcoral', alpha=0.8))

        mean = sentiment_scores.mean()
        median = sentiment_scores.median()
        std = sentiment_scores.std()

        # Calculate positive/negative percentages
        positive_count = len(sentiment_scores[sentiment_scores > 0])
        negative_count = len(sentiment_scores[sentiment_scores < 0])
        neutral_count = len(sentiment_scores[sentiment_scores == 0])
        total_count = len(sentiment_scores)
        
        positive_pct = (positive_count / total_count) * 100
        negative_pct = (negative_count / total_count) * 100
        neutral_pct = (neutral_count / total_count) * 100

        stats_text = f'Mean: {mean:.3f}\nMedian: {median:.3f}\nStd Dev: {std:.3f}\nCount: {len(sentiment_scores)}'
        plt.text(0.02, 0.98, stats_text, transform=plt.gca().transAxes, 
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        # Add sentiment breakdown
        sentiment_text = f'Positive: {positive_pct:.1f}%\nNegative: {negative_pct:.1f}%\nNeutral: {neutral_pct:.1f}%'
        plt.text(0.02, 0.7, sentiment_text, transform=plt.gca().transAxes, 
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
        
        plt.legend()
        plt.tight_layout()
        
        if save_to_db:
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
            img_buffer.seek(0)
            image_bytes = img_buffer.getvalue()
            
            success = db.save_visualization(session, round_num, year, 'histogram', image_bytes)
            if success:
                print(f"Histogram saved to database for {session}, Round {round_num}, {year}")
            else:
                print(f"Failed to save histogram to database")
            
            img_buffer.close()
        
        plt.close()

        print(f"\nSentiment Analysis Summary for {session}, Round {round_num}, {year}:")
        print(f"Total posts/comments analyzed: {len(sentiment_scores)}")
        print(f"Positive sentiment: {positive_pct:.1f}% ({positive_count} posts)")
        print(f"Negative sentiment: {negative_pct:.1f}% ({negative_count} posts)")
        print(f"Neutral sentiment: {neutral_pct:.1f}% ({neutral_count} posts)")
        print(f"Average sentiment: {mean:.3f}")
        print(f"Median sentiment: {median:.3f}")
        print(f"Standard deviation: {std:.3f}")
        print(f"Most negative score: {sentiment_scores.min():.3f}")
        print(f"Most positive score: {sentiment_scores.max():.3f}")
    
    except Exception as e:
        logging.error(f"Error creating visualization: {e}")
        print(f"Error: {e}")

def visualize_sentiment_timeline(db: F1Database, year: int, round_num: int, session: str, save_to_db: bool = True):
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

        df_clean['hour'] = df_clean['created_at'].dt.floor('h')
        hourly_avg = df_clean.groupby('hour')['vader_score'].agg(['mean', 'count']).reset_index()

        plt.figure(figsize=(14, 8))
        
        ax = plt.gca()
        
        line = plt.plot(hourly_avg['hour'], hourly_avg['mean'], marker='o', linewidth=3, markersize=8, 
                color='blue', label='Average Sentiment', zorder=3)
        
        plt.axhline(y=0, color='black', linestyle='--', linewidth=2, alpha=0.8, label='Neutral Sentiment (0)', zorder=2)
        
        positive_mask = hourly_avg['mean'] > 0
        negative_mask = hourly_avg['mean'] < 0
        
        if positive_mask.any():
            plt.fill_between(hourly_avg['hour'], 0, hourly_avg['mean'], 
                            where=positive_mask, alpha=0.3, color='green', label='Positive Sentiment')
        
        if negative_mask.any():
            plt.fill_between(hourly_avg['hour'], hourly_avg['mean'], 0, 
                            where=negative_mask, alpha=0.3, color='red', label='Negative Sentiment')
        
        if len(hourly_avg) > 1:
            hourly_stats = df_clean.groupby('hour')['vader_score'].agg(['mean', 'count', 'std']).reset_index()
            
            plt.fill_between(hourly_stats['hour'], 
                            hourly_stats['mean'] - hourly_stats['std'],
                            hourly_stats['mean'] + hourly_stats['std'],
                            alpha=0.2, color='blue', label='±1 Std Dev', zorder=1)

        plt.xlabel('Time', fontsize=12)
        plt.ylabel('Average Sentiment Score (VADER)', fontsize=12)
        plt.title(f'Sentiment Timeline - {session}, Round {round_num}, {year}', fontsize=14, fontweight='bold')
        plt.grid(True, alpha=0.3, zorder=1)
        plt.legend(loc='upper right', fontsize=10)
        plt.xticks(rotation=45)

        plt.text(0.7, 0.95, 'POSITIVE\nSENTIMENT', transform=ax.transAxes, 
                fontsize=12, fontweight='bold', color='green', ha='center', va='top',
                bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.8))
        plt.text(0.3, 0.05, 'NEGATIVE\nSENTIMENT', transform=ax.transAxes, 
                fontsize=12, fontweight='bold', color='red', ha='center', va='bottom',
                bbox=dict(boxstyle='round', facecolor='lightcoral', alpha=0.8))

        overall_mean = df_clean['vader_score'].mean()
        
        positive_count = len(df_clean[df_clean['vader_score'] > 0])
        negative_count = len(df_clean[df_clean['vader_score'] < 0])
        neutral_count = len(df_clean[df_clean['vader_score'] == 0])
        total_count = len(df_clean)
        
        positive_pct = (positive_count / total_count) * 100
        negative_pct = (negative_count / total_count) * 100
        neutral_pct = (neutral_count / total_count) * 100
        
        trend_text = f'Overall Average: {overall_mean:.3f}\nTime Points: {len(hourly_avg)}\nTotal Posts: {len(df_clean)}'
        plt.text(0.02, 0.98, trend_text, transform=ax.transAxes, 
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
        
        sentiment_text = f'Positive: {positive_pct:.1f}%\nNegative: {negative_pct:.1f}%\nNeutral: {neutral_pct:.1f}%'
        plt.text(0.02, 0.7, sentiment_text, transform=ax.transAxes, 
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        plt.tight_layout()
        
        if save_to_db:
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
            img_buffer.seek(0)
            image_bytes = img_buffer.getvalue()
            
            success = db.save_visualization(session, round_num, year, 'timeline', image_bytes)
            if success:
                print(f"Timeline saved to database for {session}, Round {round_num}, {year}")
            else:
                print(f"Failed to save timeline to database")
            
            img_buffer.close()
        
        #plt.show()
        plt.close()

        print(f"\nTimeline Analysis for {session}, Round {round_num}, {year}:")
        print(f"Time range: {df_clean['created_at'].min()} to {df_clean['created_at'].max()}")
        print(f"Overall average sentiment: {overall_mean:.3f}")
        print(f"Positive sentiment: {positive_pct:.1f}% ({positive_count} posts)")
        print(f"Negative sentiment: {negative_pct:.1f}% ({negative_count} posts)")
        print(f"Neutral sentiment: {neutral_pct:.1f}% ({neutral_count} posts)")
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
    parser.add_argument("--no-save", action="store_true", help="Don't save visualizations to database")
    args = parser.parse_args()

    db = F1Database()
    db.add_visualizations_table()
    
    try:
        save_to_db = not args.no_save
        visualize_sentiment_histogram(db, args.year, args.round, args.session, save_to_db)
        visualize_sentiment_timeline(db, args.year, args.round, args.session, save_to_db)

    except Exception as e:
        logging.error(f"Error in main: {e}")
        print(f"Error: {e}")

if __name__ == "__main__":
    main()