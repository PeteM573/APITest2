# sources.py (v14 - Final Production Version)

import requests
from bs4 import BeautifulSoup
import time
import re

# Selenium Imports
from selenium import webdriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.firefox import GeckoDriverManager

# --- CANARY MEDIA HANDLERS ---
def crawl_canary_media_links(category_url, page=1):
    if page > 1: return []
    print(f"🕵️  Crawling Canary Media: {category_url}")
    articles_found = []
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(category_url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'lxml')
        for item in soup.select('li.py-5'):
            link_tag = item.select_one('a.type-gamma')
            subsector_tag = item.select_one('p.type-theta')
            if link_tag and 'href' in link_tag.attrs:
                articles_found.append({
                    'url': link_tag['href'],
                    'subsector': subsector_tag.get_text(strip=True) if subsector_tag else 'Not Specified'
                })
        print(f"   -> Found {len(articles_found)} articles.\n")
        return articles_found
    except Exception as e:
        print(f"   -> 🔴 Error crawling Canary Media: {e}")
        return []

def scrape_canary_media_article(url):
    print(f"  Scraping URL: {url}")
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'lxml')
        title = soup.find('title').get_text(strip=True) if soup.find('title') else "Title not found"
        content_div = soup.find('div', class_='prose')
        content = content_div.get_text(separator='\n', strip=True) if content_div else "Content not found."
        return title, content
    except Exception as e:
        print(f"   -> Error scraping article: {e}")
        return None, None

# --- CLEANTECHNICA HANDLERS ---
def crawl_cleantechnica_links(search_url, page=1):
    query = search_url.split('?')[1] if '?' in search_url else ""
    base_url = search_url.split('?')[0]
    full_url = search_url if page == 1 else f"{base_url}page/{page}/?{query}"
    print(f"🕵️  Crawling CleanTechnica Search: {full_url}")
    articles_found = []
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(full_url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'lxml')
        for article_tag in soup.find_all('article'):
            link_tag = article_tag.select_one('div.cm-featured-image > a')
            if link_tag and 'href' in link_tag.attrs:
                subsector = "CleanTech"
                for cls in article_tag.get('class', []):
                    if cls.startswith('category-'):
                        subsector = cls.replace('category-', '').replace('-', ' ').title()
                        break
                articles_found.append({'url': link_tag['href'], 'subsector': subsector})
        print(f"   -> Found {len(articles_found)} articles.\n")
        return articles_found
    except Exception as e:
        print(f"   -> 🔴 Error crawling CleanTechnica: {e}")
        return []

def scrape_cleantechnica_article(url):
    print(f"  Scraping URL with Firefox/Selenium: {url}")
    options = webdriver.FirefoxOptions()
    options.add_argument("--headless")
    driver = None
    try:
        driver = webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()), options=options)
        driver.set_page_load_timeout(30)
        driver.get(url)
        wait = WebDriverWait(driver, 15)
        title_tag = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'h1.cm-entry-title')))
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.cm-entry-summary')))
        title = title_tag.text.strip()
        soup = BeautifulSoup(driver.page_source, 'lxml')
        final_content_div = soup.find('div', class_='cm-entry-summary')
        if final_content_div:
            for ad_section in final_content_div.select('hr, center, .afterpost, .sharedaddy'):
                ad_section.decompose()
            content = final_content_div.get_text(separator='\n', strip=True)
        else: content = "Content not found."
        return title, content
    except Exception as e:
        print(f"   -> 🔴 Error during Firefox/Selenium scraping: {e.__class__.__name__}")
        return None, None
    finally:
        if driver: driver.quit()

# --- CTVC HANDLERS ---
def crawl_ctvc_links(base_url, page=1):
    print(f"🕵️  Crawling CTVC Newsletter with Selenium...")
    options = webdriver.FirefoxOptions()
    options.add_argument("--headless")
    driver = None
    clicks_to_perform = 3 
    try:
        driver = webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()), options=options)
        driver.set_page_load_timeout(45)
        driver.get(base_url)
        WebDriverWait(driver, 20).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div.flex-1 h3 > a')))
        time.sleep(2)
        for i in range(clicks_to_perform):
            try:
                load_more_button = driver.find_element(By.CSS_SELECTOR, "a.load-more")
                driver.execute_script("arguments[0].scrollIntoView(true);", load_more_button)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", load_more_button)
                print(f"   -> Clicked 'Load More' ({i+1}/{clicks_to_perform})...")
                time.sleep(3)
            except Exception:
                print("   -> 'Load More' button not found.")
                break
        soup = BeautifulSoup(driver.page_source, 'lxml')
        articles_found = []
        for link_tag in soup.select('div.flex-1 h3 > a'):
            if 'href' in link_tag.attrs:
                articles_found.append({
                    'url': "https://www.ctvc.co" + link_tag['href'],
                    'subsector': 'Climatetech Newsletter'
                })
        print(f"   -> Found {len(set(d['url'] for d in articles_found))} unique articles.\n")
        # Return a list of unique dicts
        return [dict(t) for t in {tuple(d.items()) for d in articles_found}]
    except Exception as e:
        print(f"   -> 🔴 Error crawling CTVC with Selenium: {e.__class__.__name__}")
        return []
    finally:
        if driver: driver.quit()

def scrape_ctvc_article(url):
    print(f"  Scraping URL: {url}")
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'lxml')
        
        title_tag = soup.find('h1')
        title = title_tag.get_text(strip=True) if title_tag else "Title not found"
        
        main_content = soup.find('div', class_=lambda c: c and 'content' in c and 'prose' in c)
        content_block = ""

        if main_content:
            deals_heading = main_content.find(['h2', 'h3'], string=lambda t: t and 'deals of the week' in t.lower())
            if deals_heading:
                print("   -> 'Deals of the Week' heading found.")
                content_parts = []
                stop_headings = ["in the news", "exits", "new funds", "pop-up", "opportunities & events", "jobs"]
                for element in deals_heading.find_next_siblings():
                    if element.name in ['h2', 'h3']:
                        element_text = element.get_text(strip=True).lower()
                        if any(stop_word in element_text for stop_word in stop_headings):
                            break
                    content_parts.append(element.get_text(separator=' ', strip=True))
                content_block = "\n".join(content_parts)
        
        return title, content_block if content_block else "Content not found."
    except Exception as e:
        print(f"   -> 🔴 Error scraping CTVC article: {e.__class__.__name__}")
        return None, None