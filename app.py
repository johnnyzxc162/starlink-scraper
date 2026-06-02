import os
import csv
import json
import re
from flask import Flask, render_template, jsonify, send_file

app = Flask(__name__)

DATA_FILE = "starlink_data.json"

EMAIL = "fundamentalssystem@gmail.com"
PASSWORD = "systemfundamentals2026"


def scrape_starlink_live():
    from playwright.sync_api import sync_playwright
    import datetime
    import time

    results = []

    with sync_playwright() as p:
        print("[*] Launching browser...")
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage"
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)
        page = context.new_page()

        print("[*] Going to Starlink account page...")
        page.goto("https://www.starlink.com/account", wait_until="domcontentloaded", timeout=60000)

        # ── LOGIN ──────────────────────────────────────────────────────────────
        try:
            page.wait_for_selector('input[type="email"], input[name="email"]', timeout=15000)
            page.fill('input[type="email"], input[name="email"]', EMAIL)
            print("[*] Email filled.")
            next_btn = page.locator("button:has-text('Next'), button[type='submit']").first
            if next_btn.is_visible():
                next_btn.click()
                time.sleep(3)
        except Exception as e:
            print(f"[!] Email step: {e}")

        try:
            page.wait_for_selector('input[type="password"], input[name="password"]', timeout=10000)
            page.fill('input[type="password"], input[name="password"]', PASSWORD)
            print("[*] Password filled.")
            page.keyboard.press("Enter")
        except Exception as e:
            print(f"[!] Password step: {e}")

        # ── 2FA WAIT ───────────────────────────────────────────────────────────
        print("\n[*] ====================================================")
        print("[*]  PAUNAWA: Kung may 2FA code — i-type mo na sa Chrome!")
        print("[*]  Hihintay ako ng 3 minuto...")
        print("[*] ====================================================\n")
        try:
            page.wait_for_url("**/account/**", timeout=180000)
            print("[OK] Logged in!")
            time.sleep(5)
        except Exception:
            print("[!] Auto-redirect timeout. Continuing anyway...")

        # ── NAVIGATE TO SERVICE LINE ───────────────────────────────────────────
        print("[*] Going to service line page...")
        page.goto(
            "https://www.starlink.com/account/service-line/AST-2293597-46342-54"
            "?selectedDevice=ut01000000-00000000-0060d786&page=0&limit=24",
            wait_until="domcontentloaded", timeout=60000
        )
        time.sleep(10)

        # ── EXTRACT MONTHLY TABS ───────────────────────────────────────────────
        # Map of tab label -> (year, month)
        target_months = [
            ("Nov", 2025, 11),
            ("Dec", 2025, 12),
            ("Jan", 2026,  1),
            ("Feb", 2026,  2),
            ("Mar", 2026,  3),
            ("Apr", 2026,  4),
            ("May", 2026,  5),
            ("Jun", 2026,  6),
        ]

        for month_name, year, month_num in target_months:
            print(f"[*] Trying month tab: {month_name}...")
            try:
                # Click the month tab
                tab = page.locator(f"text={month_name}").first
                if not tab.is_visible(timeout=3000):
                    print(f"[!] Tab '{month_name}' not visible, skipping.")
                    continue
                tab.click()
                time.sleep(4)

                # Try MUI bar chart first
                bars = []
                try:
                    page.wait_for_selector('rect.MuiBarElement-root, rect[aria-label]', timeout=8000)
                    bars = page.evaluate("""
                        () => {
                            const bars = Array.from(document.querySelectorAll(
                                'rect.MuiBarElement-series-y_0, rect.MuiBarElement-root, rect[aria-label*="GB"]'
                            ));
                            return bars.map(b => ({
                                height: parseFloat(b.getAttribute('height') || '0'),
                                y:      parseFloat(b.getAttribute('y') || '0'),
                                label:  b.getAttribute('aria-label') || ''
                            }));
                        }
                    """)
                except:
                    pass

                start_date = datetime.date(year, month_num, 1)
                count = 0

                if bars:
                    # Calculate GB from bar pixel height
                    # Use axis labels to calibrate if possible, fallback to fixed ratio
                    chart_height = 130.0
                    gb_axis_y    = 43.13
                    pixel_per_gb = (chart_height - gb_axis_y) / 20.0

                    for i, bar in enumerate(bars):
                        # Skip zero-height bars
                        if bar["height"] < 0.5:
                            continue
                        # Try aria-label first for exact GB
                        gb = None
                        if bar["label"]:
                            m = re.search(r'(\d+\.?\d*)\s*GB', bar["label"])
                            if m:
                                gb = float(m.group(1))
                        if gb is None:
                            gb = round(bar["height"] / pixel_per_gb, 2)

                        bar_date = start_date + datetime.timedelta(days=i)
                        if bar_date <= datetime.date.today():
                            results.append({
                                "date": bar_date.strftime("%B %d, %Y"),
                                "data_usage_gb": gb
                            })
                            count += 1
                else:
                    # Fallback: read GB from page text for this month
                    body = page.inner_text("body")
                    # Look for "X GB" near this month section
                    gb_matches = re.findall(r'(\d+\.?\d*)\s*GB', body)
                    # Filter out totals (usually large round numbers like 358)
                    gb_values = [float(g) for g in gb_matches if float(g) < 100]
                    for i, gb in enumerate(gb_values):
                        bar_date = start_date + datetime.timedelta(days=i)
                        if bar_date <= datetime.date.today():
                            results.append({
                                "date": bar_date.strftime("%B %d, %Y"),
                                "data_usage_gb": gb
                            })
                            count += 1

                print(f"[OK] {month_name}: {count} records extracted.")

            except Exception as e:
                print(f"[!] Error on {month_name}: {e}")

        # ── FALLBACK: local HTML backup ────────────────────────────────────────
        if not results:
            print("[*] Live DOM empty. Checking local backup...")
            if os.path.exists("Starlink.html"):
                try:
                    with open("Starlink.html", "r", encoding="utf-8") as f:
                        html_content = f.read()
                    match = re.search(r'"dailyUsage"\s*:\s*(\[.*?\])', html_content, re.DOTALL)
                    if match:
                        records = json.loads(match.group(1))
                        for r in records:
                            results.append({
                                "date": r.get("date", r.get("day", "")),
                                "data_usage_gb": r.get("totalGB", r.get("gb", r.get("usage", 0)))
                            })
                        print(f"[OK] Loaded {len(results)} records from local backup.")
                except Exception as ex:
                    print(f"[!] Local backup failed: {ex}")

        if not results:
            with open("Starlink_live_debug.html", "w", encoding="utf-8") as f:
                f.write(page.content())
            print("[!] No data — saved debug HTML to Starlink_live_debug.html")

        browser.close()

    return results


def save_csv(data, filename="starlink_usage.csv"):
    path = os.path.join(os.getcwd(), filename)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "data_usage_gb"])
        writer.writeheader()
        for row in data:
            writer.writerow(row)
    return path


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/scrape", methods=["POST"])
def api_scrape():
    try:
        data = scrape_starlink_live()
        if not data:
            return jsonify({
                "status": "error",
                "message": "Walang na-extract. Tingnan ang Starlink_live_debug.html."
            }), 400
        with open(DATA_FILE, "w") as f:
            json.dump(data, f)
        save_csv(data)
        return jsonify({"status": "success", "data": data, "count": len(data)})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/data")
def api_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            return jsonify(json.load(f))
    return jsonify([])


@app.route("/api/download")
def api_download():
    if os.path.exists(DATA_FILE):
        data = json.load(open(DATA_FILE))
    else:
        data = scrape_starlink_live()
    path = save_csv(data)
    return send_file(path, as_attachment=True, download_name="starlink_usage.csv")


if __name__ == "__main__":
    print("\n🚀 SERVER: http://127.0.0.1:5000\n")
    app.run(debug=True, port=5000)
