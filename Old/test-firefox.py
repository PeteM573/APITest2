# test_firefox.py

import time
from selenium import webdriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.firefox import GeckoDriverManager

# The URL of one of the articles that was failing
TEST_URL = "https://cleantechnica.com/2025/07/04/swiss-startup-launches-solar-gasoline-at-fossil-fuel-industry/"

print("--- Starting Firefox Driver Test ---")

driver = None
try:
    # Setup Firefox options
    options = webdriver.FirefoxOptions()
    options.add_argument("--headless") # Run in the background

    # This will automatically download and manage "geckodriver", which is Firefox's version of chromedriver
    driver = webdriver.Firefox(
        service=FirefoxService(GeckoDriverManager().install()),
        options=options
    )

    print(f"Driver initiated successfully. Navigating to URL: {TEST_URL}")
    driver.get(TEST_URL)

    # Give it a moment to load
    time.sleep(5) 

    # If we get this far, the driver is working.
    print(f"\nSUCCESS! Page title is: '{driver.title}'")
    print("\nThis confirms the issue is with Chrome/ChromeDriver. The Firefox driver is working correctly.")

except Exception as e:
    print("\n--- TEST FAILED ---")
    print("An error occurred while trying to control Firefox.")
    print(f"Error details: {e}")

finally:
    if driver:
        print("\nClosing Firefox driver.")
        driver.quit()