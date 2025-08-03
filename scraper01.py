import requests
from bs4 import BeautifulSoup

def scrape_techcrunch_article(url):
    """
    Scrapes the title and main content from a single TechCrunch article URL.
    """
    print(f" Scraping URL: {url}\n")
    
    try:
        # Set a User-Agent to mimic a browser, which is good practice
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Fetch the HTML content of the page
        response = requests.get(url, headers=headers)
        response.raise_for_status() # Raise an exception for bad status codes (404, 500, etc.)

        # Parse the HTML with BeautifulSoup
        soup = BeautifulSoup(response.content, 'lxml')

        # --- Extraction based on our blueprint ---

        # 1. Extract the Title
        title_tag = soup.find('title')
        # Clean up the title text
        title = title_tag.get_text().replace(' | TechCrunch', '').strip() if title_tag else "Title not found"

        # 2. Extract the Content
        # Find the specific div that contains the article's main body
        content_div = soup.find('div', class_='entry-content')
        
        if content_div:
            # Find all paragraph tags within that div
            paragraphs = content_div.find_all('p')
            # Join the text of all paragraphs into a single string
            content = '\n'.join([p.get_text() for p in paragraphs])
        else:
            content = "Content not found."
        
        # --- Print the results ---
        print("--- SCRAPED DATA ---")
        print(f"TITLE: {title}\n")
        print(f"CONTENT:\n{content}")
        print("\n--- END OF DATA ---")

        return title, content

    except requests.exceptions.RequestException as e:
        print(f"Error fetching the URL: {e}")
        return None, None
    except Exception as e:
        print(f"An error occurred during scraping: {e}")
        return None, None


if __name__ == "__main__":
    # The URL from your reconnaissance
    test_url = "https://techcrunch.com/2025/01/09/xocean-raises-119m-to-capture-ocean-data-with-uncrewed-surface-vessels/"
    scrape_techcrunch_article(test_url)