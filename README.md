# Starlink Daily Data Usage Scraper

A Flask web application that parses a locally saved Starlink account HTML page
to extract daily data usage and export it to CSV.

## Features
- Web UI (Frontend) to trigger scraping and view results in a table
- BeautifulSoup-based HTML parser (no login required — uses saved HTML file)
- Exports data to `data_usage.csv`
- Download CSV directly from the browser

## Requirements
- Python 3.8+
- The provided `Starlink.html` file (already included in the repo)

## Setup & Run

# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/starlink-scraper.git
cd starlink-scraper

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
python app.py

# 4. Open in browser
Go to: http://127.0.0.1:5000

## Usage
1. Click "Scrape Data" — the app will parse Starlink.html and extract daily usage
2. Results appear in the table on the page
3. Click "Download CSV" to save the data locally

## How It Works
The scraper reads a locally saved copy of the Starlink account page (Starlink.html).
It uses BeautifulSoup to extract daily data usage values from the SVG bar chart,
then saves the results to data_usage.csv.

## Project Structure
starlink-scraper/
├── app.py              # Flask backend
├── scraper.py          # BeautifulSoup scraper logic
├── requirements.txt    # Python dependencies
├── Starlink.html       # Saved Starlink account page (source data)
├── data_usage.csv      # Output CSV (generated after scraping)
└── templates/
    └── index.html      # Frontend UIs