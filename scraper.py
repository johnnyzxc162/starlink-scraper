import time
import csv
import re
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ── CONFIGURATION ──────────────────────────────────────────────────────────
EMAIL    = ""      
PASSWORD = ""              
LOGIN_URL      = "https://www.starlink.com/auth/login"
DATA_USAGE_URL = "https://www.starlink.com/account/service-line/AST-2293597-46342-54?selectedDevice=ut01000000-00000000-0060d786&page=0&limit=24"
CSV_FILE       = "data_usage.csv"
DEBUG_FILE     = "debug_dump.txt"

SKIP_LABELS = {"current total", "total", "summary", "data used", "data usage"}
MONTH_NAMES = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec',
               'January','February','March','April','May','June','July','August',
               'September','October','November','December']

def get_driver(headless=False):
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(options=options)
    return driver

def is_skip_label(label):
    return any(skip in label.lower() for skip in SKIP_LABELS)

def parse_aria_label(label):
    if is_skip_label(label):
        return None
    m = re.search(r'([A-Za-z]{3}\s+\d{1,2}\s*[-]\s*[A-Za-z]{3}\s+\d{1,2},?\s*\d{4}).*?(\d+\.?\d*)\s*GB', label, re.IGNORECASE)
    if m:
        return {"date": m.group(1).strip(), "usage_gb": m.group(2)}
    m = re.search(r'^([A-Za-z]+ \d{4}).*?(\d+\.?\d*)\s*GB', label)
    if m:
        return {"date": m.group(1), "usage_gb": m.group(2)}
    return None

def dump_debug(driver, raw_labels, body_text):
    with open(DEBUG_FILE, "w", encoding="utf-8") as f:
        f.write("CURRENT URL:\n" + driver.current_url + "\n\n")
        f.write(f"ALL aria-label*=GB ({len(raw_labels)} found):\n")
        for i, lbl in enumerate(raw_labels):
            f.write(f"  [{i}] {lbl!r}\n")
        f.write("\nBODY TEXT (first 5000 chars):\n")
        f.write(body_text[:5000])
    print(f"[Debug] Saved -> {DEBUG_FILE}")

def wait_for_login(driver, timeout=180):
    print(f"\n[System] Hihintay ng {timeout} seconds para ma-detect ang login...")
    start = time.time()
    while time.time() - start < timeout:
        url = driver.current_url
        if "/auth/" not in url and ("account" in url or "service-line" in url):
            print("[System] Login detected!")
            return True
        time.sleep(1)
    return False

def extract_by_text_pairing(body_text):
    """
    Starlink layout sa debug dump:
      Nov
      Dec
      Jan
      ...
      20 GB
      60 GB
      ...
    Pairs months with GB values positionally.
    """
    lines = [l.strip() for l in body_text.splitlines() if l.strip()]
    
    month_lines = []
    gb_lines = []

    for line in lines:
        # Pure month name or "Nov 2024" style
        if any(line == m or line.startswith(m + ' ') for m in MONTH_NAMES):
            # Skip if it's part of nav/footer noise (very short check)
            month_lines.append(line)
        # GB value like "20 GB", "358 GB", "20.5 GB"
        elif re.match(r'^\d+\.?\d*\s*GB$', line):
            gb_lines.append(line)

    print(f"[System] Text months found: {month_lines}")
    print(f"[System] Text GB values found: {gb_lines}")

    # Remove the "Total Data Usage" GB if it's the only one
    # (total appears as single outlier — if months > gb values, skip last GB)
    rows = []
    if len(gb_lines) >= len(month_lines) and month_lines:
        for i, month in enumerate(month_lines):
            gb_val = gb_lines[i].replace('GB', '').strip()
            rows.append({"date": month, "usage_gb": gb_val})
    
    return rows

def scrape_starlink():
    driver = get_driver(headless=False)
    data_rows = []

    try:
        print("\n[System] Binubuksan ang Starlink portal...")
        driver.get(LOGIN_URL)
        time.sleep(3)

        current = driver.current_url
        print(f"[System] URL: {current}")

        # Handle homepage redirect
        if "auth/login" not in current:
            print("[System] Naka-redirect sa homepage. Hahanapin ang Sign In...")
            try:
                menu_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR,
                        "button[aria-label*='menu' i], nav button:last-child, "
                        "[class*='hamburger'], button[class*='menu' i]"
                    ))
                )
                menu_btn.click()
                time.sleep(1.5)
            except:
                print("[System] Walang menu button.")

            try:
                sign_in = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH,
                        "//*[normalize-space(text())='Sign In' or normalize-space(text())='Sign in']"
                    ))
                )
                sign_in.click()
                print("[System] Sign In clicked.")
                time.sleep(3)
            except Exception as e:
                print(f"[System] Sign In button not found: {e}. I-click mo manually.")
                time.sleep(5)

        # Email
        try:
            email_f = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.NAME, "email")))
            email_f.clear()
            email_f.send_keys(EMAIL)
            time.sleep(1)
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))).click()
            print("[System] Email submitted.")
        except Exception as e:
            print(f"[System] Email error: {e}")

        # Password
        try:
            pass_f = WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.NAME, "password")))
            time.sleep(0.5)
            pass_f.clear()
            pass_f.send_keys(PASSWORD)
            time.sleep(1)
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))).click()
            print("[System] Password submitted.")
        except Exception as e:
            print(f"[System] Password error: {e}")

        # 2FA wait
        print("\n[System] Hihintay ng 2FA... I-type mo ang code sa Chrome window.")
        logged_in = wait_for_login(driver, timeout=180)

        if not logged_in:
            print("[System] Timeout.")
            driver.save_screenshot("login_timeout.png")
            return []

        # Go to data page
        print("[System] Pumupunta sa analytics page...")
        driver.get(DATA_USAGE_URL)
        print("[System] Hihintay ng 45 seconds...")
        time.sleep(45)

        # Get body text and aria labels
        body_text = driver.execute_script("return document.body.innerText")
        raw_labels = driver.execute_script("""
            let r = [];
            document.querySelectorAll('[aria-label*="GB"]').forEach(e => r.push(e.getAttribute('aria-label')));
            return r;
        """)
        dump_debug(driver, raw_labels, body_text)

        # METHOD 1: Text pairing (matches Starlink's actual DOM structure)
        print("[System] METHOD 1: Text line pairing...")
        data_rows = extract_by_text_pairing(body_text)
        if data_rows:
            print(f"[System] Method 1 success: {len(data_rows)} cycles!")

        # METHOD 2: aria-label fallback
        if not data_rows and raw_labels:
            print("[System] METHOD 2: aria-label parse...")
            for lbl in raw_labels:
                parsed = parse_aria_label(lbl)
                if parsed:
                    data_rows.append(parsed)

        # METHOD 3: Date range text scan
        if not data_rows:
            print("[System] METHOD 3: date-range scan...")
            matches = re.findall(
                r'([A-Za-z]{3}\s+\d{1,2}\s*[-]\s*[A-Za-z]{3}\s+\d{1,2},?\s*\d{4}).*?(\d+\.?\d*)\s*GB',
                body_text, re.IGNORECASE
            )
            for cycle, gb in matches:
                data_rows.append({"date": cycle.strip(), "usage_gb": gb})

        # Dedup
        seen = set()
        unique = []
        for row in data_rows:
            key = (row["date"], row["usage_gb"])
            if key not in seen:
                seen.add(key)
                unique.append(row)
        data_rows = unique

        # Save
        if data_rows:
            with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["date", "usage_gb"])
                writer.writeheader()
                writer.writerows(data_rows)
            print(f"[System] Sync Complete! {len(data_rows)} billing cycles saved.")
        else:
            print(f"[System] Walang data. Tingnan ang {DEBUG_FILE}")

        return data_rows

    except Exception as e:
        print(f"[System] Error: {e}")
        import traceback; traceback.print_exc()
        return []
    finally:
        print("[System] Isinasara na ang browser.")
        driver.quit()
