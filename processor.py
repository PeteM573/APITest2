import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import os
import json
import csv
import time
from dotenv import load_dotenv  # NEW: Import the dotenv library
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

# NEW: Load environment variables from a .env file
load_dotenv() 

processed_urls = set()

# --- CONFIGURATION ---
client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key=os.environ.get("OPENAI_API_KEY"),
  default_headers={
    "HTTP-Referer": "https://github.com/PeteM573/APITest2",
    "X-Title": "Climate Tech Funding Tracker",
  },
)

# NEW, SELENIUM-POWERED CRAWLER FUNCTION
def crawl_for_article_links(category_url, page=1):
    """
    Crawls a specific page of a TechCrunch category using a real browser
    to handle JavaScript-based pagination.
    """
    full_url = f"{category_url}page/{page}/"
    print(f"🕵️  Crawling with a browser on: {full_url}")
    links = []
    
    # Setup Chrome options to run in "headless" mode (no visible browser window)
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    driver = None  # Initialize driver to None
    try:
        # Initialize the Chrome driver automatically
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
        
        # Load the page
        driver.get(full_url)
        
        # Give the JavaScript a moment to load the content
        time.sleep(3) 
        
        # Get the page source *after* JavaScript has run
        page_source = driver.page_source
        
        # Now, use BeautifulSoup on the JavaScript-rendered HTML
        soup = BeautifulSoup(page_source, 'lxml')
        
        for link_tag in soup.find_all('a', class_='loop-card__title-link'):
            if link_tag and 'href' in link_tag.attrs:
                clean_link = link_tag['href'].split('?')[0]
                links.append(clean_link)
        
        print(f"   -> Found {len(links)} unique article links on this page.\n")
        return links

    except Exception as e:
        print(f"   -> 🔴 Error crawling with Selenium: {e}")
        return []
    finally:
        # IMPORTANT: Always close the browser instance
        if driver:
            driver.quit()

# --- SCRAPER FUNCTION (No changes here) ---
def scrape_techcrunch_article(url):
    """Scrapes the title, content, and a soup object from a TechCrunch article."""
    print(f"  Scraping URL: {url}")
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'lxml')
        title_tag = soup.find('title')
        title = title_tag.get_text().replace(' | TechCrunch', '').strip() if title_tag else "Title not found"
        content_div = soup.find('div', class_='entry-content')
        content = '\n'.join([p.get_text() for p in content_div.find_all('p')]) if content_div else "Content not found."
        return title, content, soup # Return the soup object for our new function
    except Exception as e:
        print(f"   -> Error during scraping: {e}")
        return None, None, None

def is_climate_tech_startup(article_soup):
    """
    Checks if a startup is in the climate tech sector by scraping its own website.
    Returns True if it's climate tech, False otherwise.
    """
    print("🔍 Final Check: Validating if startup is climate tech...")
    try:
        # Step 1: Find the startup's website from the article's first paragraph
        first_p = article_soup.find('div', class_='entry-content').find('p')
        startup_link_tag = first_p.find('a') if first_p else None

        if not startup_link_tag or 'href' not in startup_link_tag.attrs:
            print("   -> Could not find startup link in article. Assuming not climate tech.")
            return False

        startup_url = startup_link_tag['href']
        
        # Step 2: Scrape the startup's homepage
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(startup_url, headers=headers, timeout=10)
        response.raise_for_status()
        startup_soup = BeautifulSoup(response.content, 'lxml')
        
        # Get all visible text from the body
        startup_text = startup_soup.body.get_text(separator=' ', strip=True)[:1500]

        # Step 3: Classify with AI
        prompt = f"""You are a climate tech industry analyst. Based on the text from a company's website, is this a climate tech company?
        
        Climate tech includes sectors like: renewable energy, grid technology, electric vehicles (EVs), sustainable agriculture, carbon capture/removal, circular economy, climate adaptation, and industrial decarbonization.
        
        Answer with only YES or NO.

        Website Text: "{startup_text}"
        
        Is this a climate tech company?
        Answer:"""
        
        messages = [{"role": "user", "content": prompt}]
        
        ai_response = client.chat.completions.create(
            model="mistralai/mistral-7b-instruct",
            messages=messages,
            temperature=0,
            max_tokens=5
        )
        
        decision = ai_response.choices[0].message.content.strip().upper()
        print(f"   -> Startup validation result: {decision}")
        return "YES" in decision

    except Exception as e:
        print(f"   -> 🔴 Error during startup validation: {e}. Assuming not climate tech.")
        return False

# --- AI FUNCTION 1: The Bouncer (No changes here) ---
# UPGRADED CLASSIFIER WITH A DIRECT COMMAND
def classify_article_type(title, content_snippet):
    """
    Uses AI to classify the article type with a direct command to be concise.
    """
    print("🤖 AI Step 1: Classifying article type (using direct command)...")

    # A more forceful prompt telling the model to be concise.
    prompt = f"""You are a news classification AI. Your task is to classify an article into one of three categories. Do not explain your reasoning. Respond with ONLY the category name.

Categories: STARTUP_FUNDING_ROUND, FUND_ANNOUNCEMENT, GENERAL_NEWS.

Example 1:
Title: "Amogy raises $80M to power ships with ammonia"
Category: STARTUP_FUNDING_ROUND

Example 2:
Title: "How a startup found an electrifying way to slash copper costs"
Category: GENERAL_NEWS

---
Classify this article:
Title: "{title}"
Snippet: "{content_snippet[:500]}"
Category:"""
    
    messages = [{"role": "user", "content": prompt}]
    
    try:
        response = client.chat.completions.create(
            # model="qwen/qwen3-8b:free",
            model="mistralai/mistral-7b-instruct",
            messages=messages,
            temperature=0,
            max_tokens=250 # A safe, generous budget.
        )
        
        classification = response.choices[0].message.content.strip()
        
        if not classification or not any(cat in classification for cat in ["STARTUP_FUNDING_ROUND", "FUND_ANNOUNCEMENT", "GENERAL_NEWS"]):
             print(f"   -> 🔴 DEBUG: Model returned an unexpected or empty classification: '{classification}'. Defaulting to GENERAL_NEWS.")
             classification = "GENERAL_NEWS"
        
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
        # model="qwen/qwen3-8b:free", # OpenRouter uses model names directly
        model="meta-llama/llama-3-8b-instruct",
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
if __name__ == "__main__":
    TECHCRUNCH_VENTURE_URL = "https://techcrunch.com/category/venture/"
    
    TARGET_SUCCESSES = 5   # Let's aim for 5 pure climate tech funding events
    MAX_PAGES_TO_CRAWL = 10  # Safety limit to avoid infinite loops

    print(f"🎯 Goal: Find {TARGET_SUCCESSES} new CLIMATE TECH funding events. Will crawl up to {MAX_PAGES_TO_CRAWL} pages.")

    all_funding_data = []
    current_page = 1

    while len(all_funding_data) < TARGET_SUCCESSES and current_page <= MAX_PAGES_TO_CRAWL:
        print(f"\n--- Crawling Page {current_page} ---")
        article_urls = crawl_for_article_links(TECHCRUNCH_VENTURE_URL, page=current_page)

        if not article_urls:
            print("   -> No more articles found on this page. Ending process.")
            break

        for url in article_urls:

            if url in processed_urls:
                continue # Skip this URL, we've already processed it.
    
             # Add the URL to our set so we don't process it again
            processed_urls.add(url)
                # --- END FIX ---
            print(f"\n--- Processing URL: {url} | Successes: {len(all_funding_data)}/{TARGET_SUCCESSES} ---")
            
            title, content, soup = scrape_techcrunch_article(url)
            
            if not title or not content or not soup:
                continue

            article_type = classify_article_type(title, content)
            
            if "STARTUP_FUNDING_ROUND" in article_type:
                funding_data = extract_funding_data(content)
                
                if funding_data and funding_data.get('startup_name'):
                    # This is our final, crucial filter
                    if is_climate_tech_startup(soup):
                        funding_data['source_url'] = url 
                        all_funding_data.append(funding_data)
                        print("   -> ✅✅✅ SUCCESS: CLIMATE TECH funding event found and saved!\n")
                        # If we hit our target, we can stop
                        if len(all_funding_data) >= TARGET_SUCCESSES:
                            break
                    else:
                        print("   -> ❌ SKIPPED: Startup is not climate tech.\n")
                else:
                    print("   -> ❌ SKIPPED: AI failed to extract startup name.\n")
            else:
                print("   -> ❌ SKIPPED: Article is not a funding announcement.\n")
            
            time.sleep(3.1)
        
        current_page += 1
        
        # Break the outer loop if we're already done
        if len(all_funding_data) >= TARGET_SUCCESSES:
            break

    save_to_csv(all_funding_data, filename="climate_funding_data.csv")
    print("🏁 Full process complete.")