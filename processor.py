import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import os
import json
import csv
import time
from dotenv import load_dotenv  # NEW: Import the dotenv library

# NEW: Load environment variables from a .env file
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

def crawl_for_article_links(category_url, limit=5):
    """
    Crawls a TechCrunch category page to find links to individual articles.
    """
    print(f"🕵️  Crawling for article links at: {category_url}")
    links = []
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(category_url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'lxml')
        
        # --- THE FIX IS HERE ---
        # We are now targeting the <a> tag directly with its specific class.
        for link_tag in soup.find_all('a', class_='loop-card__title-link'):
            # The 'href' attribute contains the URL we want.
            if link_tag and 'href' in link_tag.attrs:
                # Clean up any potential tracking parameters from the URL
                clean_link = link_tag['href'].split('?')[0]
                links.append(clean_link)
                
                # Stop once we've reached our limit
                if len(links) >= limit:
                    break
                        
        print(f"   -> Found {len(links)} article links.\n")
        return links
    except Exception as e:
        print(f"   -> Error crawling for links: {e}")
        return []

# --- SCRAPER FUNCTION (No changes here) ---
def scrape_techcrunch_article(url):
    """Scrapes the title and main content from a single TechCrunch article URL."""
    print(f" Scraping URL: {url}\n")
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'lxml')
        title_tag = soup.find('title')
        title = title_tag.get_text().replace(' | TechCrunch', '').strip() if title_tag else "Title not found"
        content_div = soup.find('div', class_='entry-content')
        if content_div:
            paragraphs = content_div.find_all('p')
            content = '\n'.join([p.get_text() for p in paragraphs])
            return title, content
        return title, "Content not found."
    except Exception as e:
        print(f"Error during scraping: {e}")
        return None, None

# --- AI FUNCTION 1: The Bouncer (No changes here) ---
def classify_article_type(title, content_snippet):
    """Uses AI to classify the article type to filter out irrelevant news."""
    print("🤖 AI Step 1: Classifying article type...")
    
    prompt = f"""
    Read the following article title and snippet. Is this article announcing that a *specific, named startup* has just raised a round of *private venture capital* (e.g., seed, Series A, B, C)?
    
    Answer with only one of these three categories:
    1. STARTUP_FUNDING_ROUND
    2. FUND_ANNOUNCEMENT (e.g., a VC announces a new fund)
    3. GENERAL_NEWS (e.g., market analysis, IPO, opinion piece)

    Title: {title}
    Snippet: {content_snippet[:400]}
    
    Category:
    """
    
    response = client.chat.completions.create(
        model="qwen/qwen3-8b:free",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=100
    )
# UPGRADED "FEW-SHOT" CLASSIFIER WITH ENHANCED DEBUGGING
def classify_article_type(title, content_snippet):
    """
    Uses AI to classify the article type with a few-shot prompt for better reliability.
    """
    print("🤖 AI Step 1: Classifying article type (using few-shot prompt)...")

    # This prompt now includes examples to guide the model.
    prompt = f"""You are an expert AI assistant who classifies financial news. Your only job is to respond with one of three categories: STARTUP_FUNDING_ROUND, FUND_ANNOUNCEMENT, or GENERAL_NEWS.

Here are some examples:

---
Example 1:
Title: "Climate-tech startup Amogy raises $80M to power ships with ammonia"
Snippet: "Amogy, a startup developing ammonia-based power solutions, announced today it has closed a Series C funding round of $80 million led by..."
Category: STARTUP_FUNDING_ROUND
---
Example 2:
Title: "How a new startup found an electrifying way to slash copper costs"
Snippet: "A New Jersey-based company has developed a new manufacturing process that could revolutionize the copper industry by reducing waste and energy consumption..."
Category: GENERAL_NEWS
---

Now, classify the following article:

Article to classify:
Title: "{title}"
Snippet: "{content_snippet[:500]}"
Category:"""
    
    messages = [{"role": "user", "content": prompt}]
    
    try:
        response = client.chat.completions.create(
            model="qwen/qwen3-8b:free",
            messages=messages,
            temperature=0,
            max_tokens=150
        )
        
        # --- ENHANCED LOGGING ---
        # We will print the entire response object to see everything.
        print(f"   -> 🔴 DEBUG: Full API response object: {response}")
        # --- END LOGGING ---

        classification = response.choices[0].message.content.strip()
        
        if not classification:
             classification = "GENERAL_NEWS" # Default if the response is empty
        
        print(f"   -> Classification result: {classification}\n")
        return classification
    except Exception as e:
        print(f"   -> 🔴 ERROR during classification: {e}. Defaulting to GENERAL_NEWS.")
        return "GENERAL_NEWS"

# --- AI FUNCTION 2: The Miner (No changes here) ---
def extract_funding_data(content):
    """Uses AI to extract structured data from the article content."""
    print("🤖 AI Step 2: Extracting structured data...")

    prompt = f"""
    From the following article text, extract the name of the startup that was funded, the total amount raised (as a string, e.g., '$119 million'), the funding stage (e.g., 'Series A', 'Seed', etc. If not mentioned, use 'Not Specified'), and a list of the investors.
    
    Provide the output as a clean JSON object with the following keys: "startup_name", "amount_raised", "funding_stage", "investors".

    Article Text:
    ---
    {content}
    ---
    """

    response = client.chat.completions.create(
        model="qwen/qwen3-8b:free", # OpenRouter uses model names directly
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": prompt}]
    )

    try:
        extracted_data = json.loads(response.choices[0].message.content)
        print(f"   -> Extraction successful!\n")
        return extracted_data
    except json.JSONDecodeError:
        print("   -> ERROR: Failed to decode JSON from AI response.")
        return None
    



def save_to_csv(data_list, filename="funding_data.csv"):
    """
    Saves a list of dictionaries to a CSV file.
    """
    if not data_list:
        print("No data to save.")
        return

    print(f"💾 Saving {len(data_list)} records to {filename}...")
    
    # Get the headers from the keys of the first dictionary
    headers = data_list[0].keys()
    
    with open(filename, 'w', newline='', encoding='utf-8') as output_file:
        dict_writer = csv.DictWriter(output_file, fieldnames=headers)
        dict_writer.writeheader()
        dict_writer.writerows(data_list)
        
    print("   -> Save complete.")
# REVISED MAIN ORCHESTRATOR
if __name__ == "__main__":
    TECHCRUNCH_CLIMATE_URL = "https://techcrunch.com/category/climate/"
    
    # --- NEW LOOP CONFIGURATION ---
    TARGET_SUCCESSES = 3  # Let's aim to find 3 good articles
    CRAWL_LIMIT = 15      # We'll crawl up to 15 links to find them
    
    print(f"🎯 Goal: Find {TARGET_SUCCESSES} new funding events. Will crawl up to {CRAWL_LIMIT} articles.")

    # 1. Crawl for a generous number of links
    article_urls = crawl_for_article_links(TECHCRUNCH_CLIMATE_URL, limit=CRAWL_LIMIT)
    
    all_funding_data = []
    url_index = 0

    # 2. Use a WHILE loop to process links until we hit our target or run out of links
    while len(all_funding_data) < TARGET_SUCCESSES and url_index < len(article_urls):
        url = article_urls[url_index]
        
        print(f"--- Processing URL {url_index + 1}/{len(article_urls)} | Successes {len(all_funding_data)}/{TARGET_SUCCESSES} ---")
        
        title, content = scrape_techcrunch_article(url)
        url_index += 1 # Increment index immediately to ensure we always move forward
        
        if not title or not content:
            print("   -> Skipping article due to scraping error.\n")
            time.sleep(1)
            continue

        article_type = classify_article_type(title, content)
        
        if "STARTUP_FUNDING_ROUND" in article_type:
            # This is a good one! Process it.
            paragraphs = content.strip().split('\n')
            if len(paragraphs) > 6:
                optimized_content = "\n".join(paragraphs[:3]) + "\n...\n" + "\n".join(paragraphs[-3:])
            else:
                optimized_content = content
            
            funding_data = extract_funding_data(optimized_content)
            
            if funding_data:
                funding_data['source_url'] = url 
                all_funding_data.append(funding_data) # Add to our success list
                print("   -> ✅ SUCCESS: Data extracted and added to collection.\n")
        else:
            # This one is irrelevant. The loop will continue.
            print("   -> ❌ SKIPPED: Article classified as irrelevant.\n")
        
        print("   -> Pausing for 3.1 seconds to respect rate limit...")
        time.sleep(3.1)

    # 3. Save all the collected data to a file
    if all_funding_data:
        save_to_csv(all_funding_data)
    else:
        print("🏁 Process finished. No new funding data was found in the crawled articles.")

    print("🏁 Full process complete.")