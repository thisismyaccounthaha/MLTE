import sys
import subprocess
import importlib.util
import json
import os

def _ensure_deps():
    # Check for requests specifically since that's what's failing
    if importlib.util.find_spec("requests") is None:
        # Use sys.executable to ensure we install to the same Python environment
        subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    else:
        print(f"requests is already installed.")
    
    # Optional: ensure playwright is also ready if needed
    if importlib.util.find_spec("playwright") is None:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright"])
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], 
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        print(f"playwright is already installed.")

_ensure_deps()

import requests
from playwright.sync_api import sync_playwright
from settings import cfg

USERNAME = cfg.msc_creds["user"]
PASSWORD = cfg.msc_creds["pass"]
URL_LOGIN = cfg.msc_urls["login"]
TARGET_URL = cfg.msc_urls["portal"]
URL_PORTAL_DATA = cfg.msc_urls["data"]

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
AUTH_FILE = os.path.join(SCRIPT_DIR, "auth.json")
DB_FILE = os.path.join(SCRIPT_DIR, "database.json")


def perform_auth():
    """Part 1: Authentication (Playwright)"""
    print("Authenticating...")
    with sync_playwright() as p:
        # Note: headless=False is often required in restricted corporate environments
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        page.goto(URL_LOGIN)
        page.fill('input[name="userName"]', USERNAME)
        page.fill('input[id="password"]', PASSWORD)
        page.click('button[type="submit"]')
        page.wait_for_load_state("networkidle")

        page.get_by_role("link", name="Databases").click()
        with context.expect_page() as new_page_info:
            page.get_by_role("button", name="Edit Data With SPS Portal").first.click()
        
        portal_page = new_page_info.value
        portal_page.wait_for_load_state("networkidle")
        
        # Save session
        context.storage_state(path=AUTH_FILE)
        browser.close()
        print(f"Session saved to {AUTH_FILE}")

def fetch_data():
    """Part 2: Data Retrieval (Requests)"""
    print("Preparing request...")
    if not os.path.exists(AUTH_FILE):
        print("Auth file missing!")
        return

    with open(AUTH_FILE, 'r') as f:
        auth_data = json.load(f)
    
    cookies = {c['name']: c['value'] for c in auth_data.get('cookies', [])}
    
    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Content-Type": "application/json; charset=UTF-8",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "X-Requested-With": "XMLHttpRequest"
    }

    payload = {
        "fieldSet": ["itemNumber", "descr", "itemAliasNumber", "itemGroupDescr", "itemSubGroupDescr", "supplierNumber", "supplierPartNumber", "brand", "unitCost"],
        "filterCriteria": {
            "pageNumber": 1, "pageSize": "10000", "sortDir": "asc", "sortedBy": "itemNumber",
            "fieldFilters": {"itemNumber": "", "supplierNumber": "", "itemGroupDescr": ""},
            "filters": []
        }
    }

    response = requests.post(URL_PORTAL_DATA, headers=headers, cookies=cookies, json=payload)
    
    if response.status_code == 200:
        data = response.json().get('items') or response.json().get('data') or []
        with open(DB_FILE, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"Success! Dumped {len(data)} items to {DB_FILE}.")
    else:
        print(f"Failed. Status Code: {response.status_code}")

def sync_database():
    """Main Orchestrator"""
    perform_auth()
    fetch_data()

if __name__ == "__main__":
    sync_database()