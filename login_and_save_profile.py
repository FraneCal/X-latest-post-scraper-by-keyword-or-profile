"""
Script to open browser and save profile after manual login.
You will login manually, then press Enter to save the browser profile.
"""
import asyncio
import os
from playwright.async_api import async_playwright

# Define the path for the browser profile directory
BROWSER_PROFILE_PATH = "browser_profile"

async def open_browser_and_wait_for_login():
    """
    Opens browser with persistent context and waits for user to manually login.
    Once user presses Enter, the browser closes and profile is saved.
    """
    async with async_playwright() as p:
        browser = None
        try:
            # Launch browser with persistent context (user data directory)
            # This will automatically save cookies, localStorage, and other session data
            # Adding extra args to make browser look more like a real user's browser
            print(f"Launching browser with profile directory: {BROWSER_PROFILE_PATH}")
            browser = await p.chromium.launch_persistent_context(
                user_data_dir=BROWSER_PROFILE_PATH,
                headless=False,
                viewport={'width': 1366, 'height': 768},  # Common laptop screen size
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='en-US',
                timezone_id='America/New_York',
                permissions=['geolocation'],
                extra_http_headers={
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                },
                args=[
                    '--disable-blink-features=AutomationControlled',  # Hide automation flags
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                ]
            )
            
            # Get the first page (persistent context creates a page automatically)
            pages = browser.pages
            if pages:
                page = pages[0]
            else:
                page = await browser.new_page()
            
            # Remove webdriver property to avoid detection
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                // Override the plugins property to use a custom getter
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                // Override the languages property to use a custom getter
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
            """)
            
            # Navigate to login page
            print("Navigating to x.com login page...")
            await page.goto("https://x.com/i/flow/login", timeout=60000, wait_until='domcontentloaded')
            await asyncio.sleep(2)  # Wait a bit for page to fully load
            
            print()
            print("=" * 60)
            print("Browser is now open. Please login manually:")
            print("1. Complete the login process in the browser")
            print("2. Handle any CAPTCHA or verification if needed")
            print("3. Make sure you're logged in and can see your home feed")
            print("4. Once logged in, come back here and press ENTER")
            print("=" * 60)
            print()
            
            # Wait for user to press Enter
            input("Press ENTER after you have successfully logged in...")
            
            # Verify login by checking if we can access home feed
            print("\nVerifying login...")
            try:
                await page.goto("https://x.com/home", timeout=60000)
                await asyncio.sleep(2)
                await page.wait_for_selector('[data-testid="primaryColumn"]', timeout=10000)
                print("✓ Login verified! Profile will be saved automatically.")
            except Exception as e:
                print(f"⚠ Warning: Could not verify login automatically: {e}")
                print("If you're sure you're logged in, the profile will still be saved.")
            
            print(f"\n✓ Browser profile will be saved to: {os.path.abspath(BROWSER_PROFILE_PATH)}")
            print("Closing browser...")
            
        except Exception as e:
            print(f"An error occurred: {e}")
        
        finally:
            if browser:
                await browser.close()
                print("Browser closed. Profile has been saved automatically.")
                print("\nYou can now use this profile in the scraper without logging in again.")

async def main():
    """Main function to run the login script."""
    print("=" * 60)
    print("X.com Browser Profile Setup")
    print("=" * 60)
    print()
    print("This script will:")
    print("1. Open a browser window")
    print("2. Navigate to x.com login page")
    print("3. Wait for you to login manually")
    print("4. Save the browser profile when you press Enter")
    print()
    
    input("Press ENTER to start...")
    print()
    
    await open_browser_and_wait_for_login()
    
    print()
    print("=" * 60)
    print("✓ Profile setup complete!")
    print("=" * 60)
    print(f"Your browser profile is saved at: {os.path.abspath(BROWSER_PROFILE_PATH)}")
    print("You can now run the scraper without logging in again.")

if __name__ == "__main__":
    asyncio.run(main())
