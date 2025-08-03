import requests
import os

# --- CONFIGURATION ---
# IMPORTANT: Replace 'YOUR_API_KEY' with the key you got from thenewsapi.com
API_KEY = 'QUgXG34Vg7Khs3kChEO2NmIIvMM31xRSaukJVzFy' 
BASE_URL = 'https://api.thenewsapi.com/v1/news/all'
ARTICLE_LIMIT = 3 # Get 3 articles per query for a quick test

# --- QUERIES TO TEST ---
QUERIES_TO_TEST = {
    "Original Query": '(funding OR investment) AND "climate tech"',
    "VC Lingo Query": '("seed round" OR "series a" OR "series b" OR "pre-seed") AND (climate OR sustainability OR decarbonization)',
    "Classic Cleantech Query": '(funding OR raised) AND cleantech',
    "Broad & Powerful Query": '(funding OR raised OR investment OR "seed round" OR "series a") AND ("climate tech" OR cleantech OR "renewable energy" OR sustainability)'
}

def run_query_experiment():
    """
    Loops through our list of test queries and prints the results for each.
    """
    if not API_KEY or API_KEY == 'YOUR_API_KEY':
        print("ERROR: Please add your API key to the script.")
        return

    for name, query in QUERIES_TO_TEST.items():
        print("="*60)
        print(f"🧪 TESTING QUERY: '{name}'")
        print(f"   Query string: '{query}'")
        print("="*60)

        params = {
            'api_token': API_KEY,
            'search': query,
            'limit': ARTICLE_LIMIT,
            'language': 'en',
            'sort': 'published_on' # Get the most recent
        }

        try:
            response = requests.get(BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()
            articles = data.get('data', [])

            if not articles:
                print("   -> No articles found for this query.\n")
                continue

            print(f"   -> Found {len(articles)} articles:\n")
            for i, article in enumerate(articles, 1):
                print(f"     --- Article {i} ---")
                print(f"       Title: {article.get('title')}")
                print(f"       URL: {article.get('url')}")
                print(f"       Snippet: {article.get('snippet', '').replace(chr(10), ' ')}")
                print()

        except requests.exceptions.RequestException as e:
            print(f"   -> ❌ An error occurred while calling the API: {e}\n")

if __name__ == "__main__":
    run_query_experiment()