# test_ctvc_extractor.py (v3 - The Correct Splitting Logic)

import time
import json
import requests
import re # Import the regular expression library
from bs4 import BeautifulSoup
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURATION ---
client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key=os.environ.get("OPENAI_API_KEY"),
  default_headers={
    "HTTP-Referer": "https://github.com/PeteM573/APITest2",
    "X-Title": "Climate Tech Funding Tracker - DIAGNOSTIC",
  },
)

TEST_URL = "https://www.ctvc.co/epa-puts-emissions-rules-in-danger-257/"

# --- The Scraper (no changes needed) ---
def scrape_ctvc_article_for_test(url):
    print(f"[SCRAPER] Scraping URL: {url}")
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'lxml')
        
        main_content = soup.find('div', class_=lambda c: c and 'content' in c and 'prose' in c)
        content = ""
        if main_content:
            deals_heading = main_content.find(['h2', 'h3'], string=lambda t: t and 'deals of the week' in t.lower())
            if deals_heading:
                print("[SCRAPER] -> 'Deals of the Week' heading found.")
                content_parts = []
                stop_headings = ["in the news", "exits", "new funds", "pop-up", "opportunities & events", "jobs"]
                for element in deals_heading.find_next_siblings():
                    if element.name in ['h2', 'h3']:
                        element_text = element.get_text(strip=True).lower()
                        if any(stop_word in element_text for stop_word in stop_headings):
                            break
                    content_parts.append(element.get_text(separator=' ', strip=True)) # Use space separator
                content = "\n".join(content_parts)
        return content if content else "Content not found."
    except Exception as e:
        print(f"[SCRAPER] -> 🔴 Error: {e}")
        return None

# --- The AI Extractor (prompt is now more robust) ---
def extract_single_deal_data(deal_string):
    print(f"\n[AI] Processing full deal: '{deal_string}'")
    prompt = f"""From the single, complete deal announcement text provided, extract the following data points: startup_name, amount_raised, funding_stage, and a list of investors.

**Instructions:**
- The startup name is the first bolded name.
- The amount is the bolded dollar/euro value.
- The funding stage is the type of funding round.
- The investors are the names listed after "from".
- If a value is not present, use `null`.

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
        extracted_data = json.loads(response.choices[0].message.content)
        print(f"[AI] -> Success: {extracted_data}")
        return extracted_data
    except Exception as e:
        print(f"[AI] -> 🔴 ERROR during data extraction: {e}")
        return None

# --- The Main Test Logic ---
if __name__ == "__main__":
    print("--- Starting CTVC Extractor Diagnostic Test ---")
    
    deals_text_block = scrape_ctvc_article_for_test(TEST_URL)

    if not deals_text_block or deals_text_block == "Content not found.":
        print("\n--- TEST FAILED: Could not scrape the deals block. ---")
    else:
        print("\n[PROCESSOR] Successfully scraped deals block. Now splitting into individual deals.")
        
        # --- THIS IS THE NEW LOGIC ---
        # 1. Use a regular expression to find all emoji characters. Emojis mark the start of a deal.
        emoji_pattern = re.compile(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F700-\U0001F77F\U0001F780-\U0001F7FF\U0001F800-\U0001F8FF\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\U00002702-\U000027B0\U000024C2-\U0001F251\U0001f926-\U0001f937\u200d\u2640-\u2642\u2600-\u2B55\u23cf\u23e9]+')
        
        # 2. Split the entire text block by these emojis.
        # The `split` will leave an empty string at the beginning, so we skip it `[1:]`.
        deal_chunks = emoji_pattern.split(deals_text_block)[1:]
        
        # 3. Find the emojis themselves, which are now the delimiters.
        emojis = emoji_pattern.findall(deals_text_block)

        # 4. Re-combine each emoji with its corresponding deal text.
        deal_lines = [emojis[i] + chunk.strip() for i, chunk in enumerate(deal_chunks)]
        
        print(f"[PROCESSOR] -> Found {len(deal_lines)} potential deals to process.")
        
        all_extracted_data = []
        for line in deal_lines:
            # We only want to process actual funding deals
            if 'raised' in line or 'funding' in line:
                time.sleep(1.5) 
                data = extract_single_deal_data(line)
                if data and data.get('startup_name'):
                    all_extracted_data.append(data)
        
        print("\n\n--- TEST COMPLETE ---")
        print(f"Successfully extracted data for {len(all_extracted_data)} deals:")
        
        import pprint
        pprint.pprint(all_extracted_data)