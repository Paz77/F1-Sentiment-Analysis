import pandas as pd
import re
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

df = pd.read_csv("f1_reddit.csv")

def clean_text(text):
    text = text.lower()
    text = re.sub(r"http\S+","", text)                
    text = re.sub(r"\[.*?\]\(.*?\)","", text)         
    text = re.sub(r"[^a-z0-9\s]"," ", text)          
    text = re.sub(r"\s+"," ", text).strip()         
    return text

df["cleaned"] = df["selftext"].fillna("") + " " + df["body"].fillna("")
df["cleaned"] = df["cleaned"].map(clean_text)