# Starlink Daily Data Usage Scraper

A Flask web application that scrapes daily data usage from your Starlink account and exports it to CSV.

## Features
- Web UI (Frontend) to trigger scraping and view results in a table
- Selenium-based login handling (email → continue → password flow)
- Exports data to `data_usage.csv`
- Download CSV directly from the browser

## Requirements
- Python 3.8+
- Google Chrome installed
- ChromeDriver (auto-managed via `webdriver-manager`)

## Setup & Run

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/starlink-scraper.git
cd starlink-scraper

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
python app.py

# 4. Open in browser
# Go to: http://127.0.0.1:5000
```

## Usage
1. Click **Scrape Data** — the app will log in to Starlink and extract daily usage
2. Results appear in the table on the page
3. Click **Download CSV** to save the data locally

## Project Structure
```
starlink-scraper/
├── app.py              # Flask backend
├── scraper.py          # Selenium scraper logic
├── requirements.txt    # Python dependencies
├── data_usage.csv      # Output CSV (generated after scraping)
└── templates/
    └── index.html      # Frontend UI
```

## Notes
- The scraper handles Starlink's two-step login (email first, then password on next screen)
- Headless Chrome is used by default; remove `--headless=new` in `scraper.py` to see the browser
