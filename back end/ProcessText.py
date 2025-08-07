import re
import nltk
import argparse
import emoji
import logging
import pandas as pd
import numpy as np
from database import F1Database
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.sentiment import SentimentIntensityAnalyzer
from textblob import TextBlob
from transformers import pipeline
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class MultiModelSentimentAnalyzer:
    def __init__(self):
        self.vader_analyzer = SentimentIntensityAnalyzer()
        self.textblob_analyzer = TextBlob

        try:
            self.bert_analyzer = pipeline(
                "sentiment-analysis", 
                model="cardiffnlp/twitter-roberta-base-sentiment-latest",
                return_all_scores=True
            )
        except Exception as e:
            logging.warning(f"BERT model not available: {e}")
            self.bert_analyzer = None

    def analyze_vader(self, text):
        try:
            scores = self.vader_analyzer.polarity_scores(text)
            return {
                'compound': scores['compound'],
                'positive': scores['pos'],
                'negative': scores['neg'],
                'neutral': scores['neu']
            }
        except Exception as e:
            logging.error(f"VADER analysis error: {e}")
            return {'compound': 0, 'positive': 0, 'negative': 0, 'neutral': 1}

    def analyze_textblob(self, text):
        try:
            blob = self.textblob_analyzer(text)
            return {
                'polarity': blob.sentiment.polarity,
                'subjectivity': blob.sentiment.subjectivity
            }
        except Exception as e:
            logging.error(f"TextBlob analysis error: {e}")
            return {'polarity': 0, 'subjectivity': 0.5}

    def analyze_bert(self, text):
        if not self.bert_analyzer:
            return {'bert_score': 0, 'bert_label': 'neutral'}
        
        try:
            if len(text) > 500:
                text = text[:500]
            
            result = self.bert_analyzer(text)[0]
            
            label_scores = {item['label']: item['score'] for item in result}
            
            if 'negative' in label_scores and 'positive' in label_scores:
                bert_score = label_scores['positive'] - label_scores['negative']
            else:
                bert_score = 0
            
            return {
                'bert_score': bert_score,
                'bert_label': max(result, key=lambda x: x['score'])['label']
            }
        except Exception as e:
            logging.error(f"BERT analysis error: {e}")
            return {'bert_score': 0, 'bert_label': 'neutral'}

    def ensemble_analysis(self, text, weights=None):
        if weights is None:
            weights = {'vader': 0.4, 'textblob': 0.3, 'bert': 0.3}

        vader_result = self.analyze_vader(text)
        textblob_result = self.analyze_textblob(text)
        bert_result = self.analyze_bert(text)

        ensemble_score = (
            vader_result['compound'] * weights['vader'] +
            textblob_result['polarity'] * weights['textblob'] +
            bert_result['bert_score'] * weights['bert']
        )

        if ensemble_score > 0.1:
            sentiment_category = 'positive'
        elif ensemble_score < -0.1:
            sentiment_category = 'negative'
        else:
            sentiment_category = 'neutral'

        return {
            'ensemble_score': ensemble_score,
            'sentiment_category': sentiment_category,
            'vader_score': vader_result['compound'],
            'textblob_polarity': textblob_result['polarity'],
            'textblob_subjectivity': textblob_result['subjectivity'],
            'bert_score': bert_result['bert_score'],
            'bert_label': bert_result['bert_label'],
            'model_agreement': self.calculate_agreement(vader_result, textblob_result, bert_result)
        }

    def calculate_agreement(self, vader_result, textblob_result, bert_result):
        scores = [
        vader_result['compound'],
        textblob_result['polarity'],
        bert_result['bert_score']
        ]
            
        std_dev = np.std(scores)
        agreement = max(0, 1 - std_dev)  
        return agreement

def get_ordinal_suffix(num):
    num = int(num)
    if 10 <= num % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(num % 10, 'th')
    return f"{num}{suffix} place"

def clean_text(text):
    try:
        if pd.isna(text) or text == "":
            return ""

        text = str(text).lower()
        text = re.sub(r"http\S+", "", text)
        text = re.sub(r"\[.*?\]\(.*?\)", "", text) 
        text = re.sub(r"\[.*?\]", "", text) 
        text = emoji.demojize(text, delimiters=(' ', ' '))

        f1_terms = {
            'drs': 'drs zone',
            'f1': 'formula one',
            'gp': 'grand prix',
            'dnf': 'did not finish',
            'dsq': 'disqualified',
            'dnq': 'did not qualify',
            'sc': 'safety car',
            'vsc': 'virtual safety car',
            'red flag': 'red flag',
            'yellow flag': 'yellow flag',
            'blue flag': 'blue flag',
            'tyres': 'tires',
            'tyre': 'tire',
            'qualifying': 'qualifying',
            'pole': 'pole position',
            'grid': 'starting grid',
            'lap': 'lap',
            'laps': 'laps',
            'overtake': 'overtake',
            'overtaking': 'overtaking',
            'championship': 'championship',
            'points': 'points',
            'penalty': 'penalty',
            'penalties': 'penalties',
            'box': 'pit box',
            'strategy': 'strategy',
            'compound': 'tire compound',
            'intermediate': 'intermediate tires',
            'wet': 'wet tires',
            'fp1': 'free practice one',
            'fp2': 'free practice two', 
            'fp3': 'free practice three',
        }

        pattern = '|'.join(r'\b' + re.escape(term) + r'\b' for term in f1_terms.keys())
        text = re.sub(pattern, lambda m: f1_terms[m.group().lower()], text, flags=re.IGNORECASE)
        
        text = re.sub(r'p\s*[-.]?\s*(\d+)', lambda m: get_ordinal_suffix(m.group(1)), text, flags=re.IGNORECASE)
        
        text = re.sub(r'(.)\1{2,}', r'\1', text)
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

    analyzer = MultiModelSentimentAnalyzer()
    logging.info("starting multi-model sentiment analysis..")

    sentiment_results = []
    for idx, row in df.iterrows():
        if idx % 100 == 0:
            logging.info(f"Processing item {idx + 1}/{len(df)}")
        
        result = analyzer.ensemble_analysis(row['cleaned'])
        sentiment_results.append(result)

    sentiment_df = pd.DataFrame(sentiment_results)
    df = pd.concat([df, sentiment_df], axis=1)
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