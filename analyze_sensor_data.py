import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from collections import defaultdict
import re
import sys
import os

CSV_FILE = "output.csv" if len(sys.argv) < 2 else sys.argv[1]

if not os.path.exists(CSV_FILE):
    print(f"Error: File '{CSV_FILE}' not found.")
    sys.exit(1)

rows = []
with open(CSV_FILE, "r") as f:
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

df = pd.DataFrame(rows)
df = df.sort_values("timestamp")

topics = df["topic"].unique()
print(f"Found {len(topics)} topics: {', '.join(topics)}")
print(f"Total data points: {len(df)}")

# Units guesses per topic keyword
def guess_unit(topic):
    t = topic.lower()
    if "temp" in t:
        return "°C"
    if "humid" in t:
        return "%"
    if "light" in t:
        return "lux"
    if "co2" in t or "gas" in t:
        return "ppm"
    return ""

n = len(topics)
cols = 2
rows_plot = (n + 1) // cols

fig, axes = plt.subplots(rows_plot, cols, figsize=(14, 4 * rows_plot))
fig.suptitle("IoT Sensor Data — comtek-6-631", fontsize=14, fontweight="bold", y=1.01)
axes = axes.flatten() if n > 1 else [axes]

colors = ["#378ADD", "#1D9E75", "#D85A30", "#7F77DD", "#BA7517", "#D4537E", "#E24B4A", "#639922", "#888780"]

for i, topic in enumerate(sorted(topics)):
    ax = axes[i]
    sub = df[df["topic"] == topic].copy()
    color = colors[i % len(colors)]
    unit = guess_unit(topic)

    ax.plot(sub["timestamp"], sub["value"], marker="o", markersize=4,
            linewidth=1.5, color=color, label=topic)
    ax.fill_between(sub["timestamp"], sub["value"], alpha=0.08, color=color)

    ax.set_title(topic, fontsize=11, fontweight="bold")
    ax.set_ylabel(unit if unit else "value", fontsize=9)
    ax.tick_params(axis="x", labelrotation=30, labelsize=8)
    ax.tick_params(axis="y", labelsize=8)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m %H:%M"))
    ax.grid(True, linestyle="--", alpha=0.4)

    stats = f"min={sub['value'].min():.1f}  max={sub['value'].max():.1f}  mean={sub['value'].mean():.1f}"
    ax.set_xlabel(stats, fontsize=8, color="#5F5E5A")

# Hide unused subplots
for j in range(i + 1, len(axes)):
    axes[j].set_visible(False)

plt.tight_layout()
out_file = "sensor_plots.png"
plt.savefig(out_file, dpi=150, bbox_inches="tight")
print(f"\nPlot saved to: {out_file}")
plt.show()
