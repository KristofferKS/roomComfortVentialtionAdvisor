#!/usr/bin/env python3
"""
Live IoT Sensor Dashboard for Raspberry Pi (Tkinter + Matplotlib)
Usage: python dashboard.py --csv TheCoolGroup.csv --refresh 5

Displays live-updating sensor readings. Click on a sensor panel to show
a graph of its recent history.
"""
import tkinter as tk
from tkinter import font
import pandas as pd
import re
import argparse
import os
from datetime import datetime, timedelta

# Matplotlib for graphing
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates

# ── Config ────────────────────────────────────────────────────────────────────
LIMITS = {
    "temperature": {"min": 20, "max": 24,  "unit": "°C",  "color": "#E07B39"},
    "humidity":    {"min": 30, "max": 60,  "unit": "%",   "color": "#39A0E0"},
    "co2":         {"min": 0,  "max": 1000,"unit": "ppm", "color": "#8BC34A"},
    "light":       {"min": 50, "max": 1000,"unit": "lux", "color": "#F5C518"},
}

TOPIC_MAP = {
    "temperature": [r"temperature_v1"],
    "humidity":    [r"humidity_v1"],
    "co2":         [r"co2_v1"],
    "light":       [r"light_v1"],
}

HISTORY_MINUTES = 90

# ── Style ─────────────────────────────────────────────────────────────────────
STYLE = {
    "BG":        "#0D0D0D",
    "PANEL_BG":  "#141414",
    "TEXT_COL":  "#E8E8E8",
    "MUTED":     "#555555",
    "WARN_COL":  "#FF4444",
    "OK_COL":    "#39FF14",
}

# ── Data Loading ──────────────────────────────────────────────────────────────
def load_data(csv_file):
    if not os.path.exists(csv_file):
        return pd.DataFrame(columns=["topic", "value", "timestamp"])
    try:
        df = pd.read_csv(csv_file, header=None, names=["userid","group","topic","value","st_label","timestamp","rt_label","rt"], usecols=[2,3,5])
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df.dropna(subset=["value", "timestamp"], inplace=True)
        df.sort_values("timestamp", inplace=True)
        return df
    except Exception as e:
        print(f"[Error loading data] {e}")
        return pd.DataFrame(columns=["topic", "value", "timestamp"])

def categorize(df):
    result = {}
    for cat, patterns in TOPIC_MAP.items():
        mask = pd.Series([False] * len(df), index=df.index)
        for pat in patterns:
            mask |= df["topic"].str.contains(pat, flags=re.IGNORECASE)
        result[cat] = df[mask].copy()
    return result

def latest_value(sub_df):
    return sub_df.iloc[-1]["value"] if not sub_df.empty else None

def recent(sub_df, minutes=HISTORY_MINUTES):
    cutoff = datetime.now() - timedelta(minutes=minutes)
    return sub_df[sub_df["timestamp"] >= cutoff]

# ── GUI Components ────────────────────────────────────────────────────────────
class SensorDisplay(tk.Frame):
    def __init__(self, parent, category, click_callback, **kwargs):
        super().__init__(parent, bg=STYLE["PANEL_BG"], bd=1, relief="solid", **kwargs)
        self.category = category
        self.limits = LIMITS[category]
        
        self.label_font = font.Font(family="monospace", size=10, weight="bold")
        self.value_font = font.Font(family="monospace", size=28, weight="bold")
        self.unit_font = font.Font(family="monospace", size=10)
        self.warn_font = font.Font(family="monospace", size=8)

        self.lbl_name = tk.Label(self, text=category.upper(), font=self.label_font, bg=STYLE["PANEL_BG"], fg=STYLE["MUTED"])
        self.lbl_name.pack(pady=(10, 0))

        self.lbl_value = tk.Label(self, text="---", font=self.value_font, bg=STYLE["PANEL_BG"], fg=self.limits["color"])
        self.lbl_value.pack(pady=5, padx=20)

        self.lbl_unit = tk.Label(self, text=self.limits["unit"], font=self.unit_font, bg=STYLE["PANEL_BG"], fg=self.limits["color"])
        self.lbl_unit.pack(pady=(0, 5))

        self.lbl_warn = tk.Label(self, text="", font=self.warn_font, bg=STYLE["PANEL_BG"], fg=STYLE["WARN_COL"])
        self.lbl_warn.pack(pady=(0, 10))

        # Bind click event to all child widgets
        self.bind_all_children("<Button-1>", lambda e: click_callback(self.category))
    
    def bind_all_children(self, event, callback):
        self.bind(event, callback)
        for child in self.winfo_children():
            child.bind(event, callback)

    def update_value(self, value):
        if value is None:
            self.lbl_value.config(text="---", fg=STYLE["MUTED"])
            self.lbl_unit.config(fg=STYLE["MUTED"])
            self.lbl_warn.config(text="")
            self.config(bd=1, relief="solid")
            return

        warn = value < self.limits["min"] or value > self.limits["max"]
        val_color = STYLE["WARN_COL"] if warn else self.limits["color"]
        
        self.lbl_value.config(text=f"{value:.1f}", fg=val_color)
        self.lbl_unit.config(fg=val_color)
        self.lbl_warn.config(text="⚠ OUT OF RANGE" if warn else "")
        self.config(bd=2 if warn else 1, relief="groove" if warn else "solid")


class DashboardApp(tk.Tk):
    def __init__(self, csv_file, refresh_sec):
        super().__init__()
        self.csv_file = csv_file
        self.refresh_ms = refresh_sec * 1000
        self.full_df = pd.DataFrame()

        self.title("IoT Sensor Dashboard")
        self.configure(bg=STYLE["BG"])
        # Set fixed size for 800x480 screen and disable resizing
        self.geometry("800x480")
        self.resizable(False, False)

        # --- Main Layout ---
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Title
        title_font = font.Font(family="monospace", size=14, weight="bold")
        self.lbl_title = tk.Label(self, text="SENSOR DASHBOARD // TheCoolGroup", font=title_font, bg=STYLE["BG"], fg=STYLE["TEXT_COL"])
        self.lbl_title.grid(row=0, column=0, pady=10)

        # Top frame for sensor panels
        top_frame = tk.Frame(self, bg=STYLE["BG"])
        top_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        
        self.displays = {}
        categories = ["temperature", "humidity", "co2", "light"]
        for i, cat in enumerate(categories):
            top_frame.grid_columnconfigure(i, weight=1)
            self.displays[cat] = SensorDisplay(top_frame, cat, self.draw_graph)
            self.displays[cat].grid(row=0, column=i, sticky="nsew", padx=5)

        # Bottom frame for graph
        graph_frame = tk.Frame(self, bg=STYLE["PANEL_BG"], bd=1, relief="solid")
        graph_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=(5, 10))
        self.setup_graph(graph_frame)

        # Status bar
        self.status_font = font.Font(family="monospace", size=8)
        self.lbl_status = tk.Label(self, text="Initializing...", font=self.status_font, bg=STYLE["BG"], fg=STYLE["MUTED"], anchor="e")
        self.lbl_status.grid(row=3, column=0, sticky="e", padx=10, pady=5)

        self.update_dashboard()
        self.movement()


    def movement(self):
        #Method for opening pir_ouput.csv and checking if the value is 1 or 0, then updating the title label accordingly
        try:
            with open("pir_output.csv", "r") as f:
                value = f.read().strip()
                if value == "1":
                    self.lbl_title.config(text="SENSOR DASHBOARD // TheCoolGroup - MOVEMENT DETECTED", fg=STYLE["TEXT_COL"])
                elif value == "0":
                    self.lbl_title.config(text="SENSOR DASHBOARD // TheCoolGroup - No movement", fg=STYLE["TEXT_COL"])
                else:
                    self.lbl_title.config(text="SENSOR DASHBOARD // TheCoolGroup - Invalid PIR value", fg=STYLE["WARN_COL"])
        except Exception as e:
            print(f"[Error reading PIR data] {e}")
            self.lbl_title.config(text="SENSOR DASHBOARD // TheCoolGroup - PIR data error", fg=STYLE["MUTED"])
        self.after(2000, self.movement) # Check every 2 seconds


    def setup_graph(self, parent_frame):
        # Adjusted figure size and DPI for 800x480 screen
        fig = Figure(figsize=(7.8, 2.5), dpi=100, facecolor=STYLE["BG"])
        # Manually set subplot padding to ensure labels fit
        fig.subplots_adjust(left=0.08, right=0.98, top=0.9, bottom=0.175)
        
        self.ax = fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(fig, master=parent_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        self.draw_graph(None) # Initial empty graph

    def draw_graph(self, category):
        self.ax.clear()
        self.ax.set_facecolor(STYLE["PANEL_BG"])
        self.ax.tick_params(axis='x', colors=STYLE["MUTED"], labelsize=7, rotation=30)
        self.ax.tick_params(axis='y', colors=STYLE["MUTED"], labelsize=7)
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.spines['bottom'].set_color(STYLE["MUTED"])
        self.ax.spines['left'].set_color(STYLE["MUTED"])
        self.ax.grid(color=STYLE["MUTED"], linestyle='--', linewidth=0.5, alpha=0.2)

        if category is None or self.full_df.empty:
            self.ax.text(0.5, 0.5, "Click a sensor panel to view graph", ha="center", va="center", color=STYLE["MUTED"], transform=self.ax.transAxes)
            self.canvas.draw()
            return

        lim = LIMITS[category]
        color = lim["color"]
        sub_df = categorize(self.full_df).get(category, pd.DataFrame())
        data = recent(sub_df)

        if data.empty:
            self.ax.text(0.5, 0.5, "No recent data for this sensor", ha="center", va="center", color=STYLE["MUTED"], transform=self.ax.transAxes)
        else:
            self.ax.plot(data["timestamp"], data["value"], color=color, linewidth=1.8)
            self.ax.fill_between(data["timestamp"], data["value"], color=color, alpha=0.15)
            
            # Comfort zone
            self.ax.axhspan(lim["min"], lim["max"], alpha=0.1, color=STYLE["OK_COL"], zorder=0)

        # Set fixed Y-axis for temperature
        if category == "temperature":
            self.ax.set_ylim(18, 28)

        self.ax.set_title(f"{category.upper()} - Last {HISTORY_MINUTES} Minutes", color=color, fontsize=9, family="monospace")
        self.ax.set_ylabel(lim["unit"], color=STYLE["MUTED"], fontsize=8, family="monospace")
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        
        self.canvas.draw()

    def update_dashboard(self):
        self.full_df = load_data(self.csv_file)
        categorized_data = categorize(self.full_df)

        for cat, display in self.displays.items():
            sub_df = categorized_data.get(cat, pd.DataFrame())
            value = latest_value(sub_df)
            display.update_value(value)
        
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.lbl_status.config(text=f"Last Update: {timestamp}")

        self.after(self.refresh_ms, self.update_dashboard)

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Live IoT sensor dashboard (Tkinter + Matplotlib)")
    parser.add_argument("--csv", default="TheCoolGroup.csv", help="Path to CSV file")
    parser.add_argument("--refresh", default=5, type=int, help="Refresh interval in seconds")
    args = parser.parse_args()

    print(f"Starting dashboard — watching '{args.csv}', refreshing every {args.refresh}s")
    print("Press Ctrl+C in terminal or close the window to exit.\n")

    app = DashboardApp(csv_file=args.csv, refresh_sec=args.refresh)
    app.mainloop()

if __name__ == "__main__":
    main()

