"""
Starlink Data Usage Scraper
============================
Parses a locally saved Starlink account HTML page to extract data usage.
Compatible with app.py — exposes scrape_starlink() that returns a list of dicts.

Usage (standalone):
    python scraper.py [path_to_html]   # default: Starlink.html
"""

from bs4 import BeautifulSoup
from datetime import date, timedelta, datetime
import csv
import sys
import os

# ── Config ────────────────────────────────────────────────────────────────────
# Path to the saved Starlink HTML file. Change this if your file is elsewhere.
HTML_FILE = "Starlink.html"

# Chart calibration (do not change unless Starlink redesigns their chart)
CHART_HEIGHT_PX = 130   # SVG chart area height in pixels
CHART_MAX_GB    = 30    # Maximum GB value on the y-axis


def parse_starlink_html(html_path: str) -> dict:
    """
    Parse a saved Starlink account HTML page and return a dict with:
      - subscription_id, nickname, service_plan
      - total_data_usage  (e.g. "459 GB")
      - device            (dict of device info)
      - daily_usage       (list of {date, usage_gb})
      - chart_start_date, chart_days
    """
    with open(html_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    result = {}
    lines = [l.strip() for l in soup.get_text(separator="\n", strip=True).splitlines() if l.strip()]

    # ── Subscription info ─────────────────────────────────────────────────────
    for line in lines:
        if line.startswith("AST-"):
            result["subscription_id"] = line
            break

    for i, line in enumerate(lines):
        if line == "Nickname" and i + 1 < len(lines):
            result["nickname"] = lines[i + 1]
            break

    for i, line in enumerate(lines):
        if line == "Service Plan" and i + 2 < len(lines):
            result["service_plan"] = lines[i + 2]
            break

    # ── Total data usage ──────────────────────────────────────────────────────
    for i, line in enumerate(lines):
        if line == "Total Data Usage" and i + 1 < len(lines):
            result["total_data_usage"] = lines[i + 1]
            break

    # ── Device info ───────────────────────────────────────────────────────────
    device = {}
    labels = {
        "Starlink ID":      "starlink_id",
        "Serial Number":    "serial_number",
        "Software Version": "software_version",
        "Kit Number":       "kit_number",
        "Uptime":           "uptime",
        "Last Updated":     "last_updated",
    }
    for i, line in enumerate(lines):
        if line in labels and i + 1 < len(lines):
            device[labels[line]] = lines[i + 1]
    result["device"] = device

    # ── Bar chart — daily usage ───────────────────────────────────────────────
    # Find chart start date from SVG x-axis text label (e.g. "Dec 16")
    start_date = None
    for svg in soup.find_all("svg"):
        for text_el in svg.find_all("text"):
            label = text_el.get_text(strip=True)
            for yr in [2024, 2025, 2026]:
                try:
                    start_date = datetime.strptime(f"{label} {yr}", "%b %d %Y").date()
                    break
                except ValueError:
                    continue
            if start_date:
                break
        if start_date:
            break

    if start_date is None:
        start_date = date(2024, 12, 16)  # safe fallback

    # Extract bar heights from the primary data series
    daily = []
    g = soup.find("g", attrs={"data-series": "y_0"})
    if g:
        for i, rect in enumerate(g.find_all("rect")):
            try:
                height_px = float(rect.get("height", 0))
            except ValueError:
                height_px = 0
            gb = round(height_px / CHART_HEIGHT_PX * CHART_MAX_GB, 2)
            day = start_date + timedelta(days=i)
            daily.append({
                "Date":           day.strftime("%Y-%m-%d"),
                "Data Usage (GB)": gb
            })

    result["daily_usage"]       = daily
    result["chart_start_date"]  = start_date.strftime("%Y-%m-%d")
    result["chart_days"]        = len(daily)
    return result


def scrape_starlink(html_path: str = HTML_FILE) -> list:
    """
    Main function called by app.py.

    Returns a list of dicts:
        [{"Date": "2024-12-16", "Data Usage (GB)": 22.85}, ...]

    Also saves results to data_usage.csv (expected by app.py /download route).
    """
    if not os.path.exists(html_path):
        error = [{"Date": "Error", "Data Usage (GB)": f"HTML file not found: {html_path}"}]
        _save_csv(error)
        return error

    try:
        parsed = parse_starlink_html(html_path)
    except Exception as e:
        error = [{"Date": "Error", "Data Usage (GB)": str(e)}]
        _save_csv(error)
        return error

    daily = parsed.get("daily_usage", [])

    # Print summary to console (visible when running via app.py)
    print(f"[Starlink Scraper]")
    print(f"  Subscription : {parsed.get('subscription_id', 'N/A')}")
    print(f"  Nickname     : {parsed.get('nickname', 'N/A')}")
    print(f"  Total Usage  : {parsed.get('total_data_usage', 'N/A')}")
    print(f"  Days parsed  : {parsed.get('chart_days', 0)}")
    print(f"  Period       : {parsed.get('chart_start_date')} — {daily[-1]['Date'] if daily else 'N/A'}")

    _save_csv(daily)
    print(f"  CSV saved    : data_usage.csv")
    return daily


def _save_csv(rows: list, path: str = "data_usage.csv"):
    """Save list of dicts to CSV."""
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


# ── Standalone CLI ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    html_file = sys.argv[1] if len(sys.argv) > 1 else HTML_FILE
    results = scrape_starlink(html_file)
    if results and results[0]["Date"] != "Error":
        print(f"\n  {'Date':<14} {'Usage (GB)':>10}")
        print(f"  {'-'*14} {'-'*10}")
        for row in results:
            print(f"  {row['Date']:<14} {row['Data Usage (GB)']:>10.2f}")
