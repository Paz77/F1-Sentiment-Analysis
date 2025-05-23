import pandas as pd
import re
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import PorterStemmer
from sklearn.feature_extraction.text import TfidfVectorizer
from nltk.sentiment import SentimentIntensityAnalyzer

def clean_text(text):
    text = text.lower()
    text = re.sub(r"http\S+","", text)                
    text = re.sub(r"\[.*?\]\(.*?\)","", text)         
    text = re.sub(r"[^a-z0-9\s]"," ", text)          
    text = re.sub(r"\s+"," ", text).strip()         
    return text

def tokenize_remove_stops(text):
    tokens = word_tokenize(text)
    return [t for t in tokens if t not in stops and len(t)>1]

nltk.download("punkt")
nltk.download("stopwords")
nltk.download("punkt_tab") 
nltk.download("vader_lexicon") 
stops = set(stopwords.words("english"))

df = pd.read_csv("f1_reddit.csv")

df["cleaned"] = df["selftext"].fillna("") + " " + df["body"].fillna("")
df["cleaned"] = df["cleaned"].map(clean_text)

df["tokens"] = df["cleaned"].map(tokenize_remove_stops)

stemmer = PorterStemmer()
df["stems"] = df["tokens"].map(lambda toks: [stemmer.stem(t) for t in toks])

docs = df["tokens"].map(" ".join)

tfidf = TfidfVectorizer(max_features=5000)  
X = tfidf.fit_transform(docs)  

sia = SentimentIntensityAnalyzer()
df["vader_score"] = df["cleaned"].map(lambda txt: sia.polarity_scores(txt)["compound"])

