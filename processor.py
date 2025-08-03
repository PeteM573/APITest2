import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import os
import json
from dotenv import load_dotenv  # NEW: Import the dotenv library

# NEW: Load environment variables from a .env file
load_dotenv() 

# --- CONFIGURATION ---
# The client will now correctly load your key from the .env file
# We also configure it to point to OpenRouter's API endpoint
# NEW: Updated client configuration for OpenRouter
client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key=os.environ.get("OPENAI_API_KEY"),
)

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
        max_tokens=50
    )
# --- AI FUNCTION 1: The Bouncer (REVISED FOR ROBUSTNESS) ---
def classify_article_type(title, content_snippet):
    """Uses AI to classify the article type to filter out irrelevant news."""
    print("🤖 AI Step 1: Classifying article type...")

    # A more robust prompt using a system message to define the AI's role
    messages = [
        {
            "role": "system",
            "content": """You are an expert AI assistant specializing in financial news analysis. Your task is to classify articles based on their content. You must respond with only one of the provided category names and nothing else."""
        },
        {
            "role": "user",
            "content": f"""Analyze the following article title and snippet. Does this article announce that a *specific, named startup* has just raised a round of *private venture capital* (e.g., seed, Series A, B, C)?

            Categories:
            1. STARTUP_FUNDING_ROUND
            2. FUND_ANNOUNCEMENT
            3. GENERAL_NEWS

            Title: {title}
            Snippet: {content_snippet[:500]}

            Category:"""
        }
    ]
    
    # Note: Double-check the exact model name on OpenRouter's site.
    # For Qwen's free model, it might be something like 'qwen/qwen-72b-chat' or 'qwen/qwen-1.8b-chat'.
    # I'll use a placeholder here.
    model_name = "qwen/qwen3-8b:free" # VERIFY THIS NAME
    
    response = client.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=0,
        max_tokens=400 # Generous token limit
    )
    
    classification = response.choices[0].message.content.strip()
    
    # Updated Logging
    print(f"   -> Raw LLM response: '{response.choices[0].message.content}'")
    print(f"   -> Classification result: {classification}\n")
    return classification

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

# --- MAIN EXECUTION (No changes here) ---
if __name__ == "__main__":
    test_url = "https://techcrunch.com/2025/01/09/xocean-raises-119m-to-capture-ocean-data-with-uncrewed-surface-vessels/"
    
    title, content = scrape_techcrunch_article(test_url)
    
    if title and content:
        article_type = classify_article_type(title, content)
        
        if "STARTUP_FUNDING_ROUND" in article_type:
            funding_data = extract_funding_data(content)
            
            if funding_data:
                print("--- FINAL PROCESSED DATA ---")
                print(json.dumps(funding_data, indent=2))
                print("\n--- END OF PROCESS ---")
        else:
            print("--- PROCESS HALTED ---")
            print("Article was classified as irrelevant and was not processed for data extraction.")
            print("\n--- END OF PROCESS ---")