# APITest: Automated Startup Funding Article Extractor

This tool automates the process of identifying and extracting structured funding data from TechCrunch articles.

## How It Works

1. **Scraping**:  
   The tool fetches a TechCrunch article and extracts its title and main content.

2. **AI Classification**:  
   It uses an LLM (via OpenRouter) to classify the article into one of three categories:
   - `STARTUP_FUNDING_ROUND`: A specific startup has raised a round of private venture capital.
   - `FUND_ANNOUNCEMENT`: A VC firm announces a new fund.
   - `GENERAL_NEWS`: Other news (e.g., market analysis, IPOs, opinion pieces).

3. **Data Extraction**:  
   If the article is classified as a startup funding round, the tool uses the LLM to extract:
   - Startup name
   - Amount raised
   - Funding stage (e.g., Series A, Seed)
   - List of investors

4. **Output**:  
   The extracted data is printed as a formatted JSON object.

## Usage

1. Add your OpenRouter API key to a `.env` file as `OPENAI_API_KEY`.
2. Run `processor.py` to process the example article or modify it to process your own URLs.

## Requirements

- Python 3.8+
- `requests`
- `beautifulsoup4`
- `openai`
- `python-dotenv`
- `lxml`

Install dependencies with:
```sh
pip install -r requirements.txt