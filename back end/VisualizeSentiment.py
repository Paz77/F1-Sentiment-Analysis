import pandas as pd 
import matplotlib.pyplot as plt 

df = pd.read_csv("Spanish Grand Prix Sentiment.csv")

plt.figure(figsize=(8, 5))
plt.hist(df["vader_score"], bins=25, edgecolor="black")
plt.title("Distribution of Spanish Grand Prix Sentiment")
plt.xlabel("Sentiment Score")
plt.ylabel("# of Posts/Comments")
plt.grid(axis="y", alpha=0.3)
plt.show()
