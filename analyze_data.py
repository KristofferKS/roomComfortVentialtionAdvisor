import pandas as pd
import matplotlib.pyplot as plt
# import matplotlib.dates as mdates
# from collections import defaultdict
import re
import sys
import os

class Data:
    def __init__(self, csv_file):
        self.csv_file = csv_file

    def to_dataframe(self):
        self.df = pd.read_csv(self.csv_file, header=None, names=["topic", "value", "timestamp"], usecols=[2, 3, 5])
        self.df["timestamp"] = pd.to_datetime(self.df["timestamp"], errors="coerce")
        self.df.sort_values("timestamp", inplace=True)
        print(self.df.to_string())


    def printer(self, topic_filter=None):
        self.to_dataframe()
        print(f"Found {len(self.df['topic'].unique())} topics")
        for topic in self.df['topic'].unique():
            print(f"Topic: {topic}")
        print(f"\nTotal data points: {len(self.df)}")
        # print for specific topic matching whole word, case-insensitive
        if topic_filter:
            for topic in topic_filter.split(", "):
                filtered_df = self.df[self.df['topic'].str.contains(rf'\b{topic}\b', flags=re.IGNORECASE)]
                print(f"\nData points for topic filter '{topic}': {len(filtered_df)}")
                print(filtered_df.to_string(index=False))
    
    def plot(self, topic_filter=None):
        self.to_dataframe()
        if topic_filter:
            for topic in topic_filter.split(", "):
                filtered_df = self.df[self.df['topic'].str.contains(rf'\b{topic}\b', flags=re.IGNORECASE)]
                plt.figure(figsize=(10, 5))
                plt.plot(filtered_df['timestamp'], filtered_df['value'])
                plt.title(f"Topic: {topic}")
                plt.xlabel("Timestamp")
                plt.ylabel("Value")
                plt.xticks(rotation=45)
                plt.tight_layout()
                plt.show()



if __name__ == "__main__":
    CSV_FILE = "output.csv"
    topic_filter = "light_v1.1, temperature_v1.1, humidity_v1.1, Co2_v1.1"

    data = Data(csv_file=CSV_FILE)
    # data.printer(topic_filter)
    data.plot(topic_filter)