# main.py (v12 - The Final Production Version)

import os
import json
import csv
import time
import re
from dotenv import load_dotenv
from openai import OpenAI
import sources

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

# --- SOURCE HANDLERS (Enable all sources for production) ---
SOURCE_HANDLERS = {
    # "Canary Media": {
    #     "url": "https://www.canarymedia.com/sections/climatetech-finance",
    #     "crawl_func": sources.crawl_canary_media_links,
    #     "scrape_func": sources.scrape_canary_media_article,
    #     "source_name": "Canary Media"
    # },
    # "CleanTechnica": {
    #     "url": "https://cleantechnica.com/?s=startup",
    #     "crawl_func": sources.crawl_cleantechnica_links,
    #     "scrape_func": sources.scrape_cleantechnica_article,
    #     "source_name": "CleanTechnica"
    # },
    "CTVC": {
        "url": "https://www.ctvc.co/tag/newsletter/",
        "crawl_func": sources.crawl_ctvc_links,
        "scrape_func": sources.scrape_ctvc_article,
        "source_name": "CTVC"
    }
}

# --- AI & UTILITY FUNCTIONS ---

def classify_article_type(title, content_snippet):
    # This is still needed for broad sources like CleanTechnica
    # ... (code is unchanged)
    print("🤖 AI Step 1: Classifying article type...")
    prompt = f"""You are an expert financial news analyst. Your SOLE task is to classify an article's purpose based on its title. Pay close attention to financial keywords.
**Keywords for STARTUP_FUNDING_ROUND:** raises, funding, secures, investment, round, closes, backed by, financing.
**Categories:** STARTUP_FUNDING_ROUND, FUND_ANNOUNCEMENT, GENERAL_NEWS
Analyze the title below and respond with ONLY the category name.
**Title:** "{title}"
**Category:**"""
    messages = [{"role": "user", "content": prompt}]
    try:
        response = client.chat.completions.create(model="mistralai/mistral-7b-instruct",messages=messages,temperature=0,max_tokens=20)
        classification = response.choices[0].message.content.strip().replace("`", "")
        if not any(cat in classification for cat in ["STARTUP_FUNDING_ROUND", "FUND_ANNOUNCEMENT", "GENERAL_NEWS"]):
             classification = "GENERAL_NEWS"
        print(f"   -> Classification result: {classification}\n")
        return classification
    except Exception as e:
        print(f"   -> 🔴 ERROR during classification: {e}")
        return "GENERAL_NEWS"


def extract_funding_data(content):
    # This is the generic extractor for single-deal articles
    # ... (code is unchanged)
    print("🤖 AI Step 2: Extracting data for VC Associate persona...")
    prompt = f"""You are a data analyst for an early-stage climate tech VC firm. Your task is to extract specific data points from the article text for a deal flow report. Be precise.
**Primary Data Points Required:**
- `startup_name`: The name of the company that received funding.
- `funding_stage`: The stage of funding (e.g., "Seed," "Series A," "pre-seed"). If not specified, use `null`.
- `amount_raised`: The total amount of money raised (e.g., "$15 million," "€20M").
- `lead_investor`: The ONE firm or individual explicitly mentioned as "leading" or "co-leading" the round. If no lead is mentioned, use `null`.
- `other_investors`: A list of any other participating investors mentioned. If none, use `null`.
**Example:**
Article Text: "Grid-X, a smart thermostat startup, has closed a $12 million Series A financing round. The investment was led by Climate Capital, with contributions from Powerhouse Ventures and Tina's Angel Fund."
JSON Output: {{"startup_name": "Grid-X", "funding_stage": "Series A", "amount_raised": "$12 million", "lead_investor": "Climate Capital", "other_investors": ["Powerhouse Ventures", "Tina's Angel Fund"]}}
---
**Actual Article to Process:**
Article Text: --- {content[:4000]} ---
JSON Output:"""
    try:
        response = client.chat.completions.create(model="meta-llama/llama-3-8b-instruct",response_format={"type": "json_object"},messages=[{"role": "user", "content": prompt}])
        extracted_data = json.loads(response.choices[0].message.content)
        return extracted_data
    except Exception as e:
        print(f"   -> 🔴 ERROR during data extraction: {e}")
        return None

def extract_ctvc_deal_data(deal_string):
    """
    NEW: A hyper-focused AI function for extracting data from a single CTVC deal string.
    """
    print(f"\n[AI] Processing deal: '{deal_string[:100]}...'")
    prompt = f"""From the single, complete deal announcement text provided, extract: startup_name, amount_raised, funding_stage, and a list of all investors.

**Instructions:**
- The startup name is the first bolded name.
- The amount is the bolded dollar/euro value.
- If a single investor is mentioned, they are the `lead_investor`.
- If multiple investors are listed after "from", the first is the `lead_investor` and the rest are `other_investors`.
- If no value is present, use `null`.

**Example:**
Text: "✈️ AIR, a Haifa, Israel-based eVTOL developer, raised $23m in Series A funding from Entrée Capital."
JSON Output: {{
  "startup_name": "AIR",
  "amount_raised": "$23m",
  "funding_stage": "Series A",
  "lead_investor": "Entrée Capital",
  "other_investors": []
}}

---
**Actual Text to Process:**
Text: "{deal_string}"
JSON Output:"""
    try:
        response = client.chat.completions.create(
            model="meta-llama/llama-3-8b-instruct",
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}]
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"[AI] -> 🔴 ERROR during data extraction: {e}")
        return None

def clean_and_normalize_data(data):
    """
    NEW: A function to clean up the messy JSON from the AI.
    """
    # Normalize different investor keys into a standard format
    lead = data.get('lead_investor') or data.get('lead_investors')
    others = data.get('other_investors') or data.get('investors')

    # Handle cases where lead is a list
    if isinstance(lead, list) and lead:
        if not others: others = []
        others.extend(lead[1:])
        lead = lead[0]
    
    cleaned_data = {
        'startup_name': data.get('startup_name'),
        'amount_raised': data.get('amount_raised'),
        'funding_stage': data.get('funding_stage'),
        'lead_investor': lead,
        'other_investors': others
    }

    # Final cleanup of null/None/'Not Specified' values
    for key, value in cleaned_data.items():
        if value is None or value == 'null' or value == ['null']:
            cleaned_data[key] = 'Not Specified'
            
    return cleaned_data


# --- UTILITY FUNCTIONS ---
def load_processed_urls(filename):
    if not os.path.exists(filename): return set()
    with open(filename, 'r', encoding='utf-8') as f:
        return set(line.strip() for line in f)

def save_to_csv(data_list, filename="climate_funding_data_master.csv"):
    if not data_list: return
    print(f"💾 Saving {len(data_list)} new records to {filename}...")
    file_exists = os.path.isfile(filename)
    headers = set().union(*(d.keys() for d in data_list))
    preferred_order = ['startup_name', 'subsector', 'amount_raised', 'funding_stage', 'lead_investor', 'other_investors', 'source_url', 'source_site']
    final_headers = sorted(list(headers), key=lambda x: preferred_order.index(x) if x in preferred_order else len(preferred_order))
    with open(filename, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=final_headers)
        if not file_exists: writer.writeheader()
        writer.writerows(data_list)
    print("   -> Save complete.")


if __name__ == "__main__":
    PROCESSED_URLS_LOG_FILE = "processed_urls.log"
    TARGET_SUCCESSES = 20 # Let's aim for a big number!
    MAX_PAGES_PER_SOURCE = 5

    processed_urls = load_processed_urls(PROCESSED_URLS_LOG_FILE)
    print(f"✅ Loaded {len(processed_urls)} previously processed URLs.")
    
    master_funding_list = []

    for name, handler in SOURCE_HANDLERS.items():
        if len(master_funding_list) >= TARGET_SUCCESSES: break
        
        print(f"\n\n{'='*60}\n⚡ Processing Source: {name}\n{'='*60}\n")
        
        current_page = 1
        
        while current_page <= MAX_PAGES_PER_SOURCE:
            if len(master_funding_list) >= TARGET_SUCCESSES: break
            
            print(f"--- Crawling Page {current_page} of {name} ---")
            articles_to_process = handler['crawl_func'](handler['url'], page=current_page)
            if not articles_to_process:
                print("   -> No more articles found for this source.")
                break

            for article_info in articles_to_process:
                if len(master_funding_list) >= TARGET_SUCCESSES: break
                
                url = article_info['url']
                if url in processed_urls: continue

                print(f"\n--- Processing URL: {url} ---")
                
                with open(PROCESSED_URLS_LOG_FILE, 'a', encoding='utf-8') as f:
                    f.write(f"{url}\n")
                processed_urls.add(url)
                
                title, content = handler['scrape_func'](url)
                if not title or not content or content == "Content not found.":
                    print("   -> ❌ SKIPPED: Scraper failed to get content.\n")
                    continue

                if name == "CTVC":
                    print("🤖 Source is CTVC, using multi-deal extraction strategy.")
                    emoji_pattern = re.compile(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001FA00-\U0001FAFF\u2600-\u26FF\u2700-\u27BF]+')
                    deal_chunks = emoji_pattern.split(content)[1:]
                    emojis = emoji_pattern.findall(content)
                    deal_lines = [emojis[i] + chunk.strip() for i, chunk in enumerate(deal_chunks)]
                    
                    print(f"   -> Found {len(deal_lines)} potential deals in this article.")
                    for deal_line in deal_lines:
                        if 'raised' in deal_line or 'funding' in deal_line:
                            time.sleep(1.5)
                            funding_data = extract_ctvc_deal_data(deal_line)
                            if funding_data:
                                cleaned_data = clean_and_normalize_data(funding_data)
                                if cleaned_data.get('startup_name') != 'Not Specified':
                                    cleaned_data['source_url'] = url
                                    cleaned_data['source_site'] = handler['source_name']
                                    cleaned_data['subsector'] = "Deal from Newsletter"
                                    master_funding_list.append(cleaned_data)
                                    print(f"   -> ✅ SUCCESS: Extracted '{cleaned_data['startup_name']}'. Total finds: {len(master_funding_list)}")
                else:
                    article_type = classify_article_type(title, content)
                    if "STARTUP_FUNDING_ROUND" in article_type:
                        funding_data = extract_funding_data(content)
                        if funding_data:
                            cleaned_data = clean_and_normalize_data(funding_data)
                            if cleaned_data.get('startup_name') != 'Not Specified':
                                cleaned_data['source_url'] = url
                                cleaned_data['source_site'] = handler['source_name']
                                cleaned_data['subsector'] = article_info['subsector']
                                master_funding_list.append(cleaned_data)
                                print(f"   -> ✅ SUCCESS: Extracted '{cleaned_data['startup_name']}'. Total finds: {len(master_funding_list)}")
                            else:
                                print("   -> ❌ SKIPPED: AI failed to extract startup name.")
                        else:
                            print("   -> ❌ SKIPPED: AI extraction returned nothing.")
                    else:
                        print("   -> ❌ SKIPPED: Article is not a funding announcement.")
                
                time.sleep(1.5)

            current_page += 1

    save_to_csv(master_funding_list)
    print(f"\n🏁 Full process complete. Added {len(master_funding_list)} new records in total.")