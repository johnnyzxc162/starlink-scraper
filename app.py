from flask import Flask, render_template, jsonify, send_file
from scraper import scrape_starlink
import os

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/scrape")
def scrape():
    data = scrape_starlink()
    return jsonify(data)

@app.route("/download")
def download():
    if os.path.exists("data_usage.csv"):
        return send_file("data_usage.csv", as_attachment=True)
    return "No CSV yet. Scrape first!", 404

if __name__ == "__main__":
    app.run(debug=True)
