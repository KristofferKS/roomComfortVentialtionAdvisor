#!/usr/bin/env python3
"""
Live IoT Sensor Dashboard for Raspberry Pi (Tkinter version)
Usage: python dashboard.py --csv comtek-6-631.csv --refresh 5

Displays live-updating sensor readings for temperature, humidity, light,
and CO2 with comfort warnings.
"""
import tkinter as tk
from tkinter import font
import pandas as pd
import re
import argparse
import os
from datetime import datetime, timedelta

# ── Config ────────────────────────────────────────────────────────────────────
LIMITS = {
    "temperature": {"min": 20, "max": 24,  "unit": "°C",  "color": "#E07B39"},
    "humidity":    {"min": 30, "max": 60,  "unit": "%",   "color": "#39A0E0"},
    "co2":         {"min": 0,  "max": 1000,"unit": "ppm", "color": "#8BC34A"},
    "light":       {"min": 50, "max": 1000,"unit": "lux", "color": "#F5C518"},
}

TOPIC_MAP = {
    "temperature": [r"temp"],
    "humidity":    [r"humid"],
    "co2":         [r"co2"],
    "light":       [r"light"],
}

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
        # Read, coercing errors and dropping rows with invalid data
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
    """Return dict of category → filtered DataFrame."""
    result = {}
    for cat, patterns in TOPIC_MAP.items():
        mask = pd.Series([False] * len(df), index=df.index)
        for pat in patterns:
            mask |= df["topic"].str.contains(pat, flags=re.IGNORECASE, na=False)
        result[cat] = df[mask].copy()
    return result

def latest_value(sub_df):
    return sub_df.iloc[-1]["value"] if not sub_df.empty else None

# ── GUI Components ────────────────────────────────────────────────────────────
class SensorDisplay(tk.Frame):
    def __init__(self, parent, category, **kwargs):
        super().__init__(parent, bg=STYLE["PANEL_BG"], bd=2, relief="groove", **kwargs)
        self.category = category
        self.limits = LIMITS[category]
        
        self.label_font = font.Font(family="monospace", size=10, weight="bold")
        self.value_font = font.Font(family="monospace", size=36, weight="bold")
        self.unit_font = font.Font(family="monospace", size=12)
        self.warn_font = font.Font(family="monospace", size=8)

        self.lbl_name = tk.Label(self, text=category.upper(), font=self.label_font, bg=STYLE["PANEL_BG"], fg=STYLE["MUTED"])
        self.lbl_name.pack(pady=(10, 0))

        self.lbl_value = tk.Label(self, text="---", font=self.value_font, bg=STYLE["PANEL_BG"], fg=self.limits["color"])
        self.lbl_value.pack(pady=5, padx=20)

        self.lbl_unit = tk.Label(self, text=self.limits["unit"], font=self.unit_font, bg=STYLE["PANEL_BG"], fg=self.limits["color"])
        self.lbl_unit.pack(pady=(0, 5))

        self.lbl_warn = tk.Label(self, text="", font=self.warn_font, bg=STYLE["PANEL_BG"], fg=STYLE["WARN_COL"])
        self.lbl_warn.pack(pady=(0, 10))

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

        self.title("IoT Sensor Dashboard")
        self.configure(bg=STYLE["BG"])
        self.geometry("800x280")

        # Title
        title_font = font.Font(family="monospace", size=14, weight="bold")
        lbl_title = tk.Label(self, text="SENSOR DASHBOARD // comtek-6-631", font=title_font, bg=STYLE["BG"], fg=STYLE["TEXT_COL"])
        lbl_title.pack(pady=15)

        # Sensor panels
        main_frame = tk.Frame(self, bg=STYLE["BG"])
        main_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.displays = {}
        categories = ["temperature", "humidity", "co2", "light"]
        for i, cat in enumerate(categories):
            self.displays[cat] = SensorDisplay(main_frame, cat)
            self.displays[cat].pack(side="left", fill="both", expand=True, padx=5)

        # Status bar
        self.status_font = font.Font(family="monospace", size=8)
        self.lbl_status = tk.Label(self, text="Initializing...", font=self.status_font, bg=STYLE["BG"], fg=STYLE["MUTED"], anchor="e")
        self.lbl_status.pack(side="right", fill="x", padx=10, pady=5)

        self.update_dashboard()

    def update_dashboard(self):
        df = load_data(self.csv_file)
        categorized_data = categorize(df)

        for cat, display in self.displays.items():
            sub_df = categorized_data.get(cat, pd.DataFrame())
            value = latest_value(sub_df)
            display.update_value(value)
        
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.lbl_status.config(text=f"Last Update: {timestamp}")
        
        self.after(self.refresh_ms, self.update_dashboard)

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Live IoT sensor dashboard (Tkinter)")
    parser.add_argument("--csv", default="comtek-6-631.csv", help="Path to CSV file")
    parser.add_argument("--refresh", default=5, type=int, help="Refresh interval in seconds")
    args = parser.parse_args()

    print(f"Starting dashboard — watching '{args.csv}', refreshing every {args.refresh}s")
    print("Press Ctrl+C in terminal or close the window to exit.\n")

    app = DashboardApp(csv_file=args.csv, refresh_sec=args.refresh)
    app.mainloop()

if __name__ == "__main__":
    main()
