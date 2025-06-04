import pandas as pd 
import matplotlib.pyplot as plt 

df = pd.read_csv("Spanish Grand Prix Sentiment.csv")

dailySentiment = df.groupby("created")["vader_score"].mean().reset_index()

plt.figure(figsize=(10, 5))
plt.plot(dailySentiment["created"],
         dailySentiment["vader_score"],
         marker="o", linestyle="-")
plt.title("Sentiment Over Time")
plt.xlabel("Date")
plt.ylabel("Sentiment Score")
plt.xticks(rotation=45)
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig("Spanish Grand Prix Sentiment.png", dpi=300)