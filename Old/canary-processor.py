# canary_processor.py (v6 - With URL Persistence)

import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import os
import json
import csv
import time
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURATION ---
client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key=os.environ.get("OPENAI_API_KEY"),
  default_headers={
    "HTTP-Referer": "https://github.com/PeteM573/APITest2",
    "X-Title": "Climate Tech Funding Tracker",
  },
)

# --- WORKER FUNCTIONS ---

def crawl_canary_media_links(category_url, page=1):
    if page == 1:
        full_url = category_url
    else:
        full_url = f"{category_url}/p{page}"
    print(f"🕵️  Crawling for articles and subsectors on: {full_url}")
    articles_found = []
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(full_url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'lxml')
        for item in soup.select('li.py-5'):
            subsector_tag = item.find('p', class_='type-theta')
            link_tag = item.find('a', class_='type-gamma')
            if link_tag and 'href' in link_tag.attrs:
                url = link_tag['href']
                subsector = subsector_tag.get_text(strip=True) if subsector_tag else 'Not Specified'
                articles_found.append({'url': url, 'subsector': subsector})
        print(f"   -> Found {len(articles_found)} articles on this page.\n")
        return articles_found
    except Exception as e:
        print(f"   -> 🔴 Error crawling Canary Media: {e}")
        return []

def scrape_canary_media_article(url):
    print(f"  Scraping URL: {url}")
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'lxml')
        title_tag = soup.find('title')
        title = title_tag.get_text().replace(' | Canary Media', '').strip() if title_tag else "Title not found"
        content_div = soup.find('div', class_='prose')
        content = content_div.get_text(separator='\n', strip=True) if content_div else "Content not found."
        return title, content
    except Exception as e:
        print(f"   -> Error during scraping: {e}")
        return None, None

# --- REUSABLE AI FUNCTIONS ---

def classify_article_type(title, content_snippet):
    print("🤖 AI Step 1: Classifying article type...")
    prompt = f"""You are a news classification AI. Classify an article into ONE of these categories: STARTUP_FUNDING_ROUND, FUND_ANNOUNCEMENT, GENERAL_NEWS. Respond with ONLY the category name.
    Article Title: "{title}"
    Snippet: "{content_snippet[:400]}"
    Category:"""
    messages = [{"role": "user", "content": prompt}]
    try:
        response = client.chat.completions.create(model="mistralai/mistral-7b-instruct", messages=messages, temperature=0, max_tokens=20)
        classification = response.choices[0].message.content.strip()
        if not any(cat in classification for cat in ["STARTUP_FUNDING_ROUND", "FUND_ANNOUNCEMENT", "GENERAL_NEWS"]):
             classification = "GENERAL_NEWS"
        print(f"   -> Classification result: {classification}\n")
        return classification
    except Exception as e:
        print(f"   -> 🔴 ERROR during classification: {e}")
        return "GENERAL_NEWS"

def extract_funding_data(content):
    print("🤖 AI Step 2: Extracting structured data (with improved prompt)...")
    prompt = f"""You are a financial analyst AI. Your task is to extract structured data from a news article about a company's funding round.
    **Instructions:**
    - Extract the startup name, the total amount raised, the funding stage, and a list of investors.
    - For the amount, capture the full string (e.g., "$15 million," "€20M").
    - If a piece of information is not mentioned, use the JSON value `null`.
    - Provide the output as a clean JSON object.
    **Example:**
    Article Text: "H2-Go, a green hydrogen startup, announced today it has secured $25 million in its Series B funding round. The round was led by Climate Capital, with participation from Future Ventures and ocean-focused investor Blue Wave Partners."
    JSON Output: {{"startup_name": "H2-Go", "amount_raised": "$25 million", "funding_stage": "Series B", "investors": ["Climate Capital", "Future Ventures", "Blue Wave Partners"]}}
    ---
    **Actual Article to Process:**
    Article Text: "{content}"
    JSON Output:"""
    try:
        response = client.chat.completions.create(model="meta-llama/llama-3-8b-instruct", response_format={"type": "json_object"}, messages=[{"role": "user", "content": prompt}])
        extracted_data = json.loads(response.choices[0].message.content)
        for key, value in extracted_data.items():
            if value is None:
                extracted_data[key] = 'Not Specified'
        print(f"   -> Extraction successful!\n")
        return extracted_data
    except Exception as e:
        print(f"   -> 🔴 ERROR during data extraction: {e}")
        return None

# --- UTILITY FUNCTIONS ---

# --- CHANGE 1: NEW FUNCTION TO LOAD PROCESSED URLS ---
def load_processed_urls(filename):
    """Loads the set of already processed URLs from a log file."""
    if not os.path.exists(filename):
        return set()
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return set(line.strip() for line in f)
    except Exception as e:
        print(f"   -> 🔴 Could not load processed URLs file: {e}")
        return set()

def save_to_csv(data_list, filename="climate_funding_data_canary.csv"):
    if not data_list:
        print("No new data to save.")
        return
    print(f"💾 Saving {len(data_list)} new records to {filename}...")
    
    # Check if file exists to determine if we need to write headers
    file_exists = os.path.isfile(filename)
    
    headers = set()
    for d in data_list:
        headers.update(d.keys())
    
    preferred_order = ['startup_name', 'subsector', 'amount_raised', 'funding_stage', 'investors', 'source_url', 'source_site']
    final_headers = sorted(list(headers), key=lambda x: preferred_order.index(x) if x in preferred_order else len(preferred_order))

    with open(filename, 'a', newline='', encoding='utf-8') as output_file: # Changed to append 'a'
        dict_writer = csv.DictWriter(output_file, fieldnames=final_headers)
        if not file_exists:
            dict_writer.writeheader()
        dict_writer.writerows(data_list)
    print("   -> Save complete.")


if __name__ == "__main__":
    CANARY_CLIMATE_FINANCE_URL = "https://www.canarymedia.com/articles/climatetech-finance"
    PROCESSED_URLS_LOG_FILE = "processed_urls.log"
    TARGET_SUCCESSES = 5
    MAX_PAGES_TO_CRAWL = 20 # We can increase this now, it's safer

    # --- CHANGE 2: LOAD THE PROCESSED URLS AT STARTUP ---
    processed_urls = load_processed_urls(PROCESSED_URLS_LOG_FILE)
    print(f"✅ Loaded {len(processed_urls)} previously processed URLs from log file.")

    all_funding_data = []
    current_page = 1

    print(f"🎯 Goal: Find {TARGET_SUCCESSES} new CLIMATE TECH funding events.")

    while len(all_funding_data) < TARGET_SUCCESSES and current_page <= MAX_PAGES_TO_CRAWL:
        print(f"\n--- Crawling Page {current_page} of Canary Media ---")
        
        articles_to_process = crawl_canary_media_links(CANARY_CLIMATE_FINANCE_URL, page=current_page)

        if not articles_to_process:
            print("   -> No more articles found. Ending process.")
            break

        for article_info in articles_to_process:
            url = article_info['url']
            subsector = article_info['subsector']
            
            # --- CHANGE 3: THE CORE PERSISTENCE LOGIC ---
            if url in processed_urls:
                # This URL is in the log file, so we skip it entirely.
                continue
            
            # This is a new URL. Process it.
            print(f"\n--- Processing URL: {url} | Successes: {len(all_funding_data)}/{TARGET_SUCCESSES} ---")
            
            # Log the URL immediately before processing to prevent re-work if the script fails.
            with open(PROCESSED_URLS_LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(f"{url}\n")
            processed_urls.add(url) # Also add to the in-memory set
            
            title, content = scrape_canary_media_article(url)
            
            if not title or not content:
                continue

            article_type = classify_article_type(title, content)
            
            if "STARTUP_FUNDING_ROUND" in article_type:
                funding_data = extract_funding_data(content)
                
                if funding_data and funding_data.get('startup_name') and funding_data.get('startup_name') != 'Not Specified':
                    funding_data['source_url'] = url 
                    funding_data['source_site'] = 'Canary Media'
                    funding_data['subsector'] = subsector
                    all_funding_data.append(funding_data)
                    print(f"   -> ✅✅✅ SUCCESS: [{subsector}] funding event found and saved!\n")
                else:
                    print("   -> ❌ SKIPPED: AI failed to extract required data.\n")
            else:
                print("   -> ❌ SKIPPED: Article is not a startup funding announcement.\n")
            
            time.sleep(1.5)

            if len(all_funding_data) >= TARGET_SUCCESSES:
                break
        
        current_page += 1
        
        if len(all_funding_data) >= TARGET_SUCCESSES:
            break

    save_to_csv(all_funding_data) # Appends new finds to the CSV
    print(f"\n🏁 Full process complete. Added {len(all_funding_data)} new records.")