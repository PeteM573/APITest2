# find_my_cache.py (v3 - The reliable version)

import os
from webdriver_manager.chrome import ChromeDriverManager

print("\n--- Forcing webdriver-manager to locate the driver ---")
print("The output below will reveal the exact cache location on your system.")
print("This may take a moment as it checks your Chrome version...")

try:
    # The .install() method is the main public function of the library.
    # It will run, find the driver, and return the full path to it.
    driver_path = ChromeDriverManager().install()

    # The returned path looks something like this:
    # /Users/your_user/.wdm/drivers/chromedriver/mac64/version/chromedriver
    # The cache root is the '.wdm' part. We can get to it by going "up" the path.
    
    # This safely navigates up the directory tree to find the root.
    cache_directory = driver_path
    for _ in range(5):
        cache_directory = os.path.dirname(cache_directory)

    print("\n" + "="*50)
    print("SUCCESS: Found the driver and determined the cache path.")
    print("\nThe driver binary is located at:")
    print(f"  {driver_path}")
    print("\nThis means the root cache directory for webdriver-manager is:")
    print(f"==> {cache_directory}")
    print("="*50 + "\n")
    print("Please use this exact path to clear the cache.")
    print(f"To delete it, run this command in your terminal:")
    print(f'\n  rm -rf "{cache_directory}"\n')
    print("(The quotes are important if the path contains spaces)")


except Exception as e:
    print(f"\nAn error occurred during the process.")
    print("This can sometimes happen if Chrome itself is not found.")
    print(f"Error details: {e}")