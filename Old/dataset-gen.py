import csv
import random
from datetime import date, timedelta

# --- 1. Define Headers ---
HEADERS = [
    "funding_date", "company_name", "amount_raised_usd", "funding_stage", 
    "investors", "climate_tech_vertical", "headquarters_country", 
    "headquarters_city", "short_description", "company_website", "source_url"
]

# --- 2. Create Pools of Mock Data ---
COMPANY_ADJECTIVES = ["Aura", "Helio", "Terra", "Aqua", "Myco", "Geo", "Atmo", "Grid"]
COMPANY_NOUNS = ["Volt", "Synth", "Gen", "Scale", "Carbon", "Cycle", "DAO", "Labs"]
FUNDING_STAGES = ["Seed", "Series A", "Series B", "Grant"]
VERTICALS = ["Energy", "Mobility", "Food & Ag", "Carbon Tech", "Industrial Decarbonization", "Climate Adaptation"]
INVESTORS = ["Breakthrough Energy Ventures", "Lowercarbon Capital", "Congruent Ventures", "Khosla Ventures", "Y Combinator", "a16z"]
COUNTRIES = {"USA": ["San Francisco", "Boston", "New York"], "Germany": ["Berlin", "Munich"], "UK": ["London"]}

# --- 3. Generate the Data ---
def generate_mock_data(num_records=25):
    funding_events = []
    for i in range(num_records):
        adj = random.choice(COMPANY_ADJECTIVES)
        noun = random.choice(COMPANY_NOUNS)
        company = f"{adj}{noun}"
        
        country = random.choice(list(COUNTRIES.keys()))
        city = random.choice(COUNTRIES[country])
        
        stage = random.choice(FUNDING_STAGES)
        amount = 0
        if stage == "Seed": amount = random.randint(1, 5) * 1_000_000
        elif stage == "Series A": amount = random.randint(10, 25) * 1_000_000
        elif stage == "Series B": amount = random.randint(30, 100) * 1_000_000
        else: amount = random.randint(100, 500) * 1_000

        event = {
            "funding_date": (date.today() - timedelta(days=random.randint(1, 365))).strftime("%Y-%m-%d"),
            "company_name": company,
            "amount_raised_usd": amount,
            "funding_stage": stage,
            "investors": "|".join(random.sample(INVESTORS, k=random.randint(1, 3))),
            "climate_tech_vertical": random.choice(VERTICALS),
            "headquarters_country": country,
            "headquarters_city": city,
            "short_description": f"Developing novel {stage.lower()} technology for the {random.choice(VERTICALS)} sector.",
            "company_website": f"https://www.{company.lower()}.com",
            "source_url": f"https://techcrunch.com/2025/01/15/{company.lower()}-raises-{amount // 1_000_000}m/"
        }
        funding_events.append(event)
    return funding_events

# --- 4. Write to CSV ---
if __name__ == "__main__":
    mock_data = generate_mock_data(25)
    
    with open('funding_events.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(mock_data)
        
    print("✅ Successfully generated 'funding_events.csv' with 25 mock records.")