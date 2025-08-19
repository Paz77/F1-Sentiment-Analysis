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

class F1SentimentLexicon:
    def __init__(self):
        self.f1_positive_words = {
            'overtake': 0.8, 'overtaking': 0.8, 'overtook': 0.8, 'overtaken': 0.8,
            'pole': 0.9, 'pole position': 0.9, 'qualifying': 0.7, 'qualified': 0.7,
            'win': 1.0, 'winner': 1.0, 'winning': 1.0, 'won': 1.0,
            'podium': 0.8, 'podium finish': 0.9, 'top three': 0.8,
            'fastest': 0.9, 'fastest lap': 0.9, 'purple sector': 0.8,
            'championship': 0.6, 'champion': 0.9, 'championship lead': 0.8,
            'points': 0.7, 'scored points': 0.8, 'point finish': 0.7,
            
            'battle': 0.6, 'racing': 0.7, 'wheel to wheel': 0.8,
            'dramatic': 0.6, 'thrilling': 0.8, 'exciting': 0.8,
            'incredible': 0.7, 'amazing': 0.8, 'fantastic': 0.8,
            'brilliant': 0.8, 'outstanding': 0.8, 'perfect': 0.9,
            
            'strategy': 0.5, 'good strategy': 0.8, 'perfect strategy': 0.9,
            'undercut': 0.7, 'overcut': 0.7, 'pit stop': 0.5,
            'fast pit stop': 0.8, 'perfect pit stop': 0.9,
            
            'pace': 0.6, 'good pace': 0.8, 'strong pace': 0.8,
            'grip': 0.6, 'good grip': 0.7, 'downforce': 0.5,
            'aerodynamics': 0.5, 'power unit': 0.5, 'engine': 0.5,
            
            'talent': 0.8, 'skilled': 0.8, 'talented': 0.8,
            'legend': 0.9, 'legendary': 0.9, 'masterclass': 0.9,
            'consistency': 0.7, 'reliable': 0.7, 'mature': 0.7,
        }

        self.f1_negative_words = {
            'crash': -0.6, 'crashed': -0.7, 'accident': -0.7, 'incident': -0.5,
            'collision': -0.7, 'contact': -0.5, 'hit': -0.6, 'hit the wall': -0.8,
            'spin': -0.6, 'spun': -0.7, 'spinning': -0.6,
            'dnf': -0.8, 'did not finish': -0.8, 'retired': -0.7,
            'dsq': -0.9, 'disqualified': -0.9, 'disqualification': -0.9,
            'dnq': -0.8, 'did not qualify': -0.8,
            
            'slow': -0.6, 'slower': -0.6, 'slowest': -0.7,
            'struggling': -0.6, 'struggle': -0.6, 'struggled': -0.6,
            'problem': -0.5, 'issues': -0.5, 'technical issues': -0.7,
            'failure': -0.7, 'mechanical failure': -0.8, 'engine failure': -0.8,
            'breakdown': -0.7, 'broken': -0.6, 'damage': -0.6,
            
            'penalty': -0.6, 'penalties': -0.6, 'penalized': -0.7,
            'mistake': -0.6, 'error': -0.6, 'blunder': -0.7,
            'lockup': -0.5, 'locked up': -0.6, 'flat spot': -0.5,
            'off track': -0.5, 'run wide': -0.5, 'cut the corner': -0.6,
            
            'safety car': -0.4, 'sc': -0.4, 'virtual safety car': -0.4, 'vsc': -0.4,
            'red flag': -0.5, 'yellow flag': -0.3, 'double yellow': -0.4,
            'blue flag': -0.3, 'lapped': -0.5, 'lapped car': -0.5,
            
            'tire wear': -0.4, 'tire degradation': -0.5, 'grain': -0.4,
            'blistering': -0.5, 'flat tire': -0.7, 'puncture': -0.7,
            'slow pit stop': -0.6, 'bad strategy': -0.6, 'wrong strategy': -0.7,
            
            'inconsistent': -0.6, 'unreliable': -0.7, 'immature': -0.6,
            'overaggressive': -0.5, 'reckless': -0.7, 'dangerous': -0.7,
        }

        self.f1_neutral_words = {
            'drs': 0.0, 'drs zone': 0.0, 'drag reduction system': 0.0,
            'kers': 0.0, 'kinetic energy recovery system': 0.0,
            'ers': 0.0, 'energy recovery system': 0.0,
            'mguk': 0.0, 'mguh': 0.0, 'turbo': 0.0,
            'hybrid': 0.0, 'battery': 0.0, 'fuel': 0.0,
            
            'chicane': 0.0, 'hairpin': 0.0, 'straight': 0.0,
            'corner': 0.0, 'turn': 0.0, 'sector': 0.0,
            'pit lane': 0.0, 'pit wall': 0.0, 'garage': 0.0,
            
            'lap': 0.0, 'laps': 0.0, 'lap time': 0.0,
            'position': 0.0, 'grid': 0.0, 'starting grid': 0.0,
            'gap': 0.0, 'interval': 0.0, 'delta': 0.0,
        }

        self.f1_context_words = {
            'crash': {
                'positive_contexts': ['exciting', 'dramatic', 'spectacular'],
                'negative_contexts': ['avoid', 'prevent', 'dangerous'],
                'default_score': -0.6
            },
            'battle': {
                'positive_contexts': ['racing', 'wheel to wheel', 'close'],
                'negative_contexts': ['avoid', 'prevent', 'dangerous'],
                'default_score': 0.6
            },
            'aggressive': {
                'positive_contexts': ['racing', 'overtaking', 'fighting'],
                'negative_contexts': ['too', 'over', 'reckless'],
                'default_score': 0.3
            }
        }

    def get_f1_sentiment_score(self, text, base_sentiment_score=0.0):
        if not text:
            return base_sentiment_score

        text_lower = text.lower()
        words = text_lower.split()

        f1_adjustment = 0.0
        word_count = 0

        for word in words:
            if word in self.f1_positive_words:
                f1_adjustment += self.f1_positive_words[word]
                word_count += 1

            elif word in self.f1_negative_words:
                f1_adjustment += self.f1_negative_words[word]
                word_count += 1

            elif word in self.f1_context_words:
                context_score = self._analyze_context_word(word, text_lower)
                f1_adjustment += context_score
                word_count += 1
        
        if word_count > 0:
            avg_f1_adjustment = f1_adjustment / word_count
            final_score = (base_sentiment_score * 0.7) + (avg_f1_adjustment * 0.3)
        else:
            final_score = base_sentiment_score
            
        return final_score

    def _analyze_context_word(self, word, text):
        context_info = self.f1_context_words[word]
        default_score = context_info['default_score']
        
        positive_context_found = any(
            context in text for context in context_info['positive_contexts']
        )
        
        negative_context_found = any(
            context in text for context in context_info['negative_contexts']
        )
        
        if positive_context_found and not negative_context_found:
            return min(default_score + 0.2, 1.0)  
        elif negative_context_found and not positive_context_found:
            return max(default_score - 0.2, -1.0)  
        else:
            return default_score

    def get_f1_keywords(self, text):
        if not text:
            return []
            
        text_lower = text.lower()
        words = text_lower.split()
        
        f1_keywords = []
        for word in words:
            if (word in self.f1_positive_words or 
                word in self.f1_negative_words or 
                word in self.f1_neutral_words or
                word in self.f1_context_words):
                f1_keywords.append(word)
                
        return f1_keywords

class MultiModelSentimentAnalyzer:
    def __init__(self):
        self.vader_analyzer = SentimentIntensityAnalyzer()
        self.textblob_analyzer = TextBlob
        self.f1_lexicon = F1SentimentLexicon()

        try:
            self.bert_analyzer = pipeline(
                "sentiment-analysis", 
                model="cardiffnlp/twitter-roberta-base-sentiment-latest",
                top_k=None  
            )
        except Exception as e:
            logging.warning(f"BERT model not available: {e}")
            self.bert_analyzer = None

    def analyze_vader(self, text):
        try:
            scores = self.vader_analyzer.polarity_scores(text)

            f1_adjusted_compound = self.f1_lexicon.get_f1_sentiment_score(
                text, scores['compound']
            )

            return {
                'compound': f1_adjusted_compound,
                'positive': scores['pos'],
                'negative': scores['neg'],
                'neutral': scores['neu'],
                'f1_keywords' : self.f1_lexicon.get_f1_keywords(text)
            }

        except Exception as e:
            logging.error(f"VADER analysis error: {e}")
            return {'compound': 0, 'positive': 0, 'negative': 0, 'neutral': 1, 'f1_keywords': []}

    def analyze_textblob(self, text):
        try:
            blob = self.textblob_analyzer(text)

            f1_adjusted_polarity = self.f1_lexicon.get_f1_sentiment_score(
                text, blob.sentiment.polarity
            )

            return {
                'polarity': f1_adjusted_polarity,
                'subjectivity': blob.sentiment.subjectivity,
                'f1_keywords' : self.f1_lexicon.get_f1_keywords(text)
            }
        except Exception as e:
            logging.error(f"TextBlob analysis error: {e}")
            return {'polarity': 0, 'subjectivity': 0.5, 'f1_keywords': []}

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
            'model_agreement': self.calculate_agreement(vader_result, textblob_result, bert_result),
            'f1_keywords': vader_result.get('f1_keywords', [])
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

    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt')
    
    stops = set(stopwords.words('english'))
    tokens = word_tokenize(text)
    
    return [t for t in tokens if t not in stops and len(t)>1]

def validate_sentiment_scores(df):
    df['sentiment_confidence'] = 0.0

    df.loc[df['cleaned'].str.len() < 10, 'sentiment_confidence'] -= 0.3

    number_count = df['cleaned'].str.count(r'\d+')
    df.loc[number_count > 3, 'sentiment_confidence'] -= 0.2

    url_count = df['text'].str.count(r'http')
    df.loc[url_count > 0, 'sentiment_confidence'] -= 0.1

    driver_team_pattern = r'\b(hamilton|verstappen|leclerc|sainz|norris|russell|alonso|stroll|ocon|gasly|tsunoda|bottas|zhou|magnussen|hulkenberg|albon|sargeant|piastri|ricciardo|mercedes|ferrari|red bull|mclaren|aston martin|alpine|haas|williams|racing bulls|rb)\b'
    driver_team_count = df['cleaned'].str.count(driver_team_pattern, flags=re.IGNORECASE)
    df.loc[driver_team_count > 2, 'sentiment_confidence'] -= 0.15

    punctuation_count = df['text'].str.count(r'[!?]{2,}')
    df.loc[punctuation_count > 0, 'sentiment_confidence'] -= 0.1

    emoji_count = df['text'].str.count(r':[a-z_]+:')
    text_length = df['text'].str.len()
    emoji_ratio = emoji_count / text_length.replace(0, 1)
    df.loc[emoji_ratio > 0.3, 'sentiment_confidence'] -= 0.2
    
    return df

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

    df = validate_sentiment_scores(df)
    low_confidence_count = len(df[df['sentiment_confidence'] < -0.3])
    total_count = len(df)
    logging.info(f"Validation complete: {low_confidence_count}/{total_count} posts flagged as low confidence")

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
    df['adjusted_ensemble_score'] = df['ensemble_score'] * (1 + df['sentiment_confidence'])
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