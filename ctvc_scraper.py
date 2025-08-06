# ctvc_scraper.py
# A focused, reusable module to scrape and extract climate tech funding deals from CTVC.

import os
import json
import csv
import time
import re
import requests
from dotenv import load_dotenv
from openai import OpenAI
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.firefox import GeckoDriverManager

# --- INITIALIZATION ---
load_dotenv()

# Configure the OpenAI client
# For Replit, these will be set in the "Secrets" (environment variables) tab.
client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key=os.environ.get("OPENAI_API_KEY"),
  default_headers={
    "HTTP-Referer": "https://github.com/your-repo", # Optional: Change to your repo URL
    "X-Title": "Climate Tech Funding Tracker",
  },
)

PROCESSED_URLS_LOG_FILE = "processed_urls.log"

# --- HELPER FUNCTIONS ---

def load_processed_urls(filename=PROCESSED_URLS_LOG_FILE):
    if not os.path.exists(filename):
        return set()
    with open(filename, 'r', encoding='utf-8') as f:
        return set(line.strip() for line in f)

def save_to_csv(data_list, filename="climate_funding_data_master.csv"):
    if not data_list:
        print("No new data to save.")
        return
    print(f"💾 Saving {len(data_list)} new records to {filename}...")
    file_exists = os.path.isfile(filename)
    headers = set().union(*(d.keys() for d in data_list))
    preferred_order = ['startup_name', 'subsector', 'amount_raised', 'funding_stage', 'lead_investor', 'other_investors', 'source_url', 'source_site']
    final_headers = sorted(list(headers), key=lambda x: preferred_order.index(x) if x in preferred_order else len(preferred_order))
    
    with open(filename, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=final_headers)
        if not file_exists:
            writer.writeheader()
        writer.writerows(data_list)
    print("   -> Save complete.")

def crawl_ctvc_links(pages_to_load=1):
    base_url = "https://www.ctvc.co/tag/newsletter/"
    print(f"🕵️  Crawling CTVC Newsletter with Selenium...")
    options = webdriver.FirefoxOptions()
    options.add_argument("--headless")
    driver = None
    
    try:
        driver = webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()), options=options)
        driver.set_page_load_timeout(45)
        driver.get(base_url)
        WebDriverWait(driver, 20).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div.flex-1 h3 > a')))
        time.sleep(2)

        for i in range(pages_to_load):
            try:
                load_more_button = driver.find_element(By.CSS_SELECTOR, "a.load-more")
                driver.execute_script("arguments[0].scrollIntoView(true);", load_more_button)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", load_more_button)
                print(f"   -> Clicked 'Load More' ({i+1}/{pages_to_load})...")
                time.sleep(3)
            except Exception:
                print("   -> 'Load More' button not found.")
                break
        
        soup = BeautifulSoup(driver.page_source, 'lxml')
        unique_urls = set()
        for link_tag in soup.select('div.flex-1 h3 > a'):
            if 'href' in link_tag.attrs:
                unique_urls.add("https://www.ctvc.co" + link_tag['href'])
        
        print(f"   -> Found {len(unique_urls)} unique articles after loading more.\n")
        return list(unique_urls)
    
    except Exception as e:
        print(f"   -> 🔴 Error crawling CTVC with Selenium: {e.__class__.__name__}")
        return []
    finally:
        if driver:
            driver.quit()

def scrape_deals_block(url):
    print(f"  Scraping URL for deals block: {url}")
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'lxml')
        
        main_content = soup.find('div', class_=lambda c: c and 'content' in c and 'prose' in c)
        if not main_content:
            return "Content not found."

        deals_heading = main_content.find(['h2', 'h3'], string=lambda t: t and 'deals of the week' in t.lower())
        if not deals_heading:
            return "Content not found."
            
        print("   -> 'Deals of the Week' heading found.")
        content_parts = []
        stop_headings = ["in the news", "exits", "new funds", "pop-up", "opportunities & events", "jobs"]
        for element in deals_heading.find_next_siblings():
            if element.name in ['h2', 'h3']:
                element_text = element.get_text(strip=True).lower()
                if any(stop_word in element_text for stop_word in stop_headings):
                    break
            content_parts.append(element.get_text(separator=' ', strip=True))
        
        return "\n".join(content_parts)
    
    except Exception as e:
        print(f"   -> 🔴 Error scraping article: {e.__class__.__name__}")
        return "Content not found."

def extract_deal_data(deal_string):
    prompt = f"""From the deal announcement text, extract: startup_name, amount_raised, funding_stage, and all investors.

**Instructions:**
- The startup name is the first bolded name.
- The amount is the bolded dollar/euro value.
- If a single investor is mentioned after "from", they are the `lead_investor`.
- If multiple investors are listed, the first is the `lead_investor` and the rest are `other_investors`.
- If a value is not present, use `null`.

**Example:**
Text: "✈️ AIR, a Haifa, Israel-based eVTOL developer, raised $23m in Series A funding from Entrée Capital."
JSON Output: {{"startup_name": "AIR", "amount_raised": "$23m", "funding_stage": "Series A", "lead_investor": "Entrée Capital", "other_investors": []}}

---
**Text to Process:** "{deal_string}"
**JSON Output:**"""
    try:
        response = client.chat.completions.create(
            model="meta-llama/llama-3-8b-instruct",
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}]
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"   -> 🔴 AI Error: {e}")
        return None

def clean_data(data):
    lead = data.get('lead_investor') or data.get('lead_investors')
    others = data.get('other_investors') or data.get('investors')
    
    if isinstance(lead, list) and lead:
        if not others: others = []
        others.extend(lead[1:])
        lead = lead[0]

    cleaned = {k: v for k, v in {
        'startup_name': data.get('startup_name'), 'amount_raised': data.get('amount_raised'),
        'funding_stage': data.get('funding_stage'), 'lead_investor': lead, 'other_investors': others
    }.items() if v is not None and v != 'null' and v != ['null']}
    
    return cleaned

# --- THE MAIN ENTRY POINT FOR YOUR UI ---

def fetch_latest_ctvc_deals(pages_to_load=1):
    """
    This is the main function the front-end will call.
    It orchestrates the entire process of scraping and extracting CTVC deals.
    
    Args:
        pages_to_load (int): The number of times to click the "Load More" button.
                             Each click loads ~6 more articles.
                             
    Returns:
        list: A list of dictionaries, where each dictionary is a funding deal.
    """
    processed_urls = load_processed_urls()
    newsletter_urls = crawl_ctvc_links(pages_to_load=pages_to_load)
    
    new_deals = []
    
    for url in newsletter_urls:
        if url in processed_urls:
            continue
            
        print(f"\n--- Processing article: {url} ---")
        deals_block = scrape_deals_block(url)
        
        if deals_block != "Content not found.":
            # Use regex to split the block by the deal-starting emojis
            emoji_pattern = re.compile(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001FA00-\U0001FAFF\u2600-\u26FF\u2700-\u27BF]+')
            deal_chunks = emoji_pattern.split(deals_block)[1:]
            emojis = emoji_pattern.findall(deals_block)
            deal_lines = [emojis[i] + chunk.strip() for i, chunk in enumerate(deal_chunks)]
            
            print(f"   -> Found {len(deal_lines)} potential deals in this article.")
            for line in deal_lines:
                if 'raised' in line or 'funding' in line:
                    time.sleep(1.5) # Rate limit our AI calls
                    deal_data = extract_deal_data(line)
                    if deal_data:
                        cleaned_data = clean_data(deal_data)
                        if cleaned_data.get('startup_name'):
                            cleaned_data['source_url'] = url
                            cleaned_data['source_site'] = "CTVC"
                            new_deals.append(cleaned_data)
                            print(f"   -> ✅ SUCCESS: Extracted '{cleaned_data['startup_name']}'")
        
        # Log the URL after we're done with it
        with open(PROCESSED_URLS_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"{url}\n")
            
    return new_deals

# --- TEST BLOCK ---
# This code only runs when you execute `python ctvc_scraper.py` directly.
# It allows you to test the module without needing a UI.
if __name__ == "__main__":
    print("--- Running in Test Mode ---")
    
    # We'll crawl 2 pages for a thorough test
    latest_deals = fetch_latest_ctvc_deals(pages_to_load=2)
    
    if latest_deals:
        print(f"\n--- TEST COMPLETE ---")
        print(f"Successfully extracted {len(latest_deals)} new deals.")
        
        # Save the results to a CSV for inspection
        save_to_csv(latest_deals)
        
        # Print a sample of the data
        import pprint
        print("\nSample of extracted data:")
        pprint.pprint(latest_deals[:5])
    else:
        print("\n--- TEST COMPLETE ---")
        print("No new deals were found.")