import pandas as pd
# import matplotlib.pyplot as plt
# import matplotlib.dates as mdates
# from collections import defaultdict
import re
import sys
import os

class Data:
    def __init__(self, csv_file):
        self.csv_file = csv_file
    
    def import_data(self):
        if not os.path.exists(self.csv_file):
            print(f"Error: File '{self.csv_file}' not found.")
            sys.exit(1)
        
        rows = []
        with open(self.csv_file, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = [p.strip() for p in line.split(",")]
                if len(parts) < 4:
                    continue

                topic = parts[2]
                try:
                    value = float(parts[3])
                except ValueError:
                    continue

                timestamp_str = None
                for i, p in enumerate(parts):
                    if p == "sample_timestamp" and i + 1 < len(parts):
                        ts_raw = parts[i + 1]
                        # Try full datetime format: "Mon Apr 13 16:21:10 2026"
                        try:
                            ts = pd.to_datetime(ts_raw, format="%a %b %d %H:%M:%S %Y")
                            timestamp_str = ts
                            break
                        except ValueError:
                            pass
                        # Try time-only format: "10:40:11" (use received timestamp day)
                        received_day = None
                        for j, q in enumerate(parts):
                            if q == "received timestamp" and j + 1 < len(parts):
                                received_raw = parts[j + 1]
                                day_match = re.match(r"(\d+)/", received_raw)
                                if day_match:
                                    received_day = int(day_match.group(1))
                                break
                        if received_day and re.match(r"^\d{2}:\d{2}:\d{2}$", ts_raw):
                            try:
                                ts = pd.to_datetime(f"2026-04-{received_day:02d} {ts_raw}")
                                timestamp_str = ts
                                break
                            except ValueError:
                                pass

                if timestamp_str is not None:
                    rows.append({"topic": topic, "value": value, "timestamp": timestamp_str})
        
        if not rows:
            print("No data parsed. Check your CSV format.")
            sys.exit(1)
        self.rows = rows
    
    def printer(self, topic_filter=None):
        df = pd.DataFrame(self.rows)
        df = df.sort_values("timestamp")

        topics = df["topic"].unique()
        print(f"Found {len(topics)} topics")
        for topic in topics:
            print(f"Topic: {topic}")
        print(f"\nTotal data points: {len(df)}")
        # print for specific topic, and allow for multiple topics if needed
        if topic_filter:
            for topic in topic_filter.split(","):
                topic_df = df[df["topic"] == topic.strip()]
                print(topic_df)


if __name__ == "__main__":
    CSV_FILE = "output.csv"
    topic_filter = "light, temp_real"

    data = Data(csv_file=CSV_FILE)
    data.import_data()
    data.printer(topic_filter)