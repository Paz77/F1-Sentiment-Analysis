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

dfSorted = df.sort_values("vader_score", ascending=False)

topPos = dfSorted.head(5).copy()
topNeg = dfSorted.tail(5).copy()

topPos["type"] = "positive"
topNeg["type"] = "negative"
topCombined = pd.concat([topPos, topNeg])

plt.figure(figsize=(10, 6))
bars = plt.bar(
    topCombined["id"], 
    topCombined["vader_score"], 
    color=["green" if t=="positive" else "red" for t in topCombined["type"]]
)
plt.xticks(rotation=90)  
plt.title("Top 5 Positive (green) and Top 5 Negative (red) Posts")
plt.ylabel("Sentiment Score")
plt.axhline(0, color="black", linewidth=0.8)  
plt.tight_layout()
plt.savefig("Spanish Grand Prix Sentiment.png", dpi=300)
