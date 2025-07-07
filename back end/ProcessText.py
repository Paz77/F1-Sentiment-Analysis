import re
import nltk
import argparse
import requests
import logging
import pandas as pd
from database import F1Database
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import PorterStemmer
from sklearn.feature_extraction.text import TfidfVectorizer
from nltk.sentiment import SentimentIntensityAnalyzer
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def clean_text(text):
    """Clean text with error handling"""
    try:
        if pd.isna(text) or text == "":
            return ""
        
        text = str(text).lower()
        text = re.sub(r"http\S+", "", text)
        text = re.sub(r"\[.*?\]\(.*?\)", "", text)
        text = re.sub(r"[^a-z0-9\s]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text
    except Exception as e:
        logging.error(f"Error cleaning text: {e}")
        return ""

def tokenize_remove_stops(text):
    try:
        nltk.data.find('corpora/stopwords')
    except LookupError:
        nltk.download('stopwords')
    
    stops = set(stopwords.words('english'))
    tokens = word_tokenize(text)
    
    return [t for t in tokens if t not in stops and len(t)>1]

def process_sentiment_from_db(race_round: int, race_year: int, session: str = ""):
    """ proccesses sentiment directly from db"""
    db = F1Database()
    
    # Create sentiment table if it doesn't exist
    db.add_sentiment_table()

    if session:
        posts = db.get_posts_by_session(session, race_round, race_year)
        comments = db.get_comments_by_round(session, race_round, race_year)
    else:
        all_data = db.get_all_sessions_by_round(race_round, race_year)
        posts = [item for item in all_data if item.get('type') == 'post']
        comments = [item for item in all_data if item.get('type') == 'comment']

    combined_texts = []
    for post in posts:
        text = f"{post.get('title', '')} {post.get('selftext', '')}"
        combined_texts.append({
            'id': post['id'],
            'text': text,
            'created': post['created'],
            'type': 'post',
            'session': post['session']
        })

    for comment in comments:
        combined_texts.append({
            'id': comment['id'],
            'text': comment.get('body', ''),
            'created': comment['created'],
            'type': 'comment',
            'session': comment['session']
        })

    df = pd.DataFrame(combined_texts)
    if df.empty:
        logging.warning(f"No data found for round {race_round}, year {race_year}, session {session}")
        return df

    if 'text' not in df.columns:
        logging.error("DataFrame missing 'text' column")
        return df

    df['cleaned'] = df['text'].map(clean_text)
    df['tokens'] = df['cleaned'].map(tokenize_remove_stops)

    sia = SentimentIntensityAnalyzer()
    df['vader_score'] = df['cleaned'].map(lambda txt: sia.polarity_scores(txt)['compound'])

    db.save_sentiment_scores(df)
    return df

def process_in_batches(df, batch_size=1000):
    """processes large datasets in batches"""
    results = []
    
    for i in range(0, len(df), batch_size):
        batch = df.iloc[i:i+batch_size]
        logging.info(f"Processing batch {i//batch_size + 1}/{(len(df)-1)//batch_size + 1}")
        
        batch['cleaned'] = batch['text'].map(clean_text)
        batch['tokens'] = batch['cleaned'].map(tokenize_remove_stops)
        
        sia = SentimentIntensityAnalyzer()
        batch['vader_score'] = batch['cleaned'].map(
            lambda txt: sia.polarity_scores(txt)['compound']
        )
        
        results.append(batch)
    
    return pd.concat(results, ignore_index=True)

def main():
    parser = argparse.ArgumentParser(description="Process sentiment analysis for F1 Reddit data")

    parser.add_argument("--year", type=int, default=datetime.now().year, help="F1 season year (default: current year)")
    parser.add_argument("--round", type=int, required=True, help="F1 race round number")
    parser.add_argument("--session", choices=["FP1", "FP2", "FP3", "Sprint Qualifying", "Sprint", "Qualifying", "Race"], help="Specific session to analyze (optional)")
    parser.add_argument("--batch_size", type=int, default=1000, help="Batch size for processing (default: 1000)")
    parser.add_argument("--save_csv", action="store_true", help="Save results to CSV file")
    
    args = parser.parse_args()

    db = F1Database()
    try:
        df = process_sentiment_from_db(
            race_round=args.round,
            race_year=args.year,
            session=args.session
        )
        
        if args.save_csv:
            race_info = db.get_race_info_by_round(args.round, args.year)
            if race_info:
                output_file = f"{race_info['race_name']}_sentiment_analysis.csv"
                df.to_csv(output_file, index=False)
                logging.info(f"Results saved to {output_file}")
        
    except Exception as e:
        logging.error(f"Error in main processing: {e}")
        raise

if __name__ == "__main__":
    main()