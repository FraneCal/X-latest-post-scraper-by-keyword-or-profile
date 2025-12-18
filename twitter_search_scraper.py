import time
import random
import json
import asyncio
from playwright.async_api import async_playwright
from datetime import datetime, timedelta # Import datetime and timedelta for date parsing
import os # Import os to check for file existence
import urllib.parse # Import urllib.parse for URL encoding
import re # Import re for regex operations

# Try to import pandas and openpyxl for Excel support
try:
    import pandas as pd
    EXCEL_SUPPORT = True
except ImportError:
    EXCEL_SUPPORT = False

def is_excel_file(filename):
    """Check if filename is an Excel file."""
    return filename and (filename.endswith('.xlsx') or filename.endswith('.xls'))

def load_existing_tweets_from_excel(filepath):
    """Load existing tweets from Excel file and convert back to tweet format."""
    if not EXCEL_SUPPORT:
        return [], set()
    
    try:
        if os.path.exists(filepath):
            df = pd.read_excel(filepath)
            tweets = []
            seen_ids = set()
            
            for _, row in df.iterrows():
                # Convert Excel row back to tweet format (using Body instead of Text)
                tweet = {
                    'id': str(row.get('ID', '')),
                    'author': str(row.get('Author', '')),
                    'username': str(row.get('Username', '')),
                    'display_name': str(row.get('Display Name', '')),
                    'body': str(row.get('Body', '')),
                    'date': str(row.get('Date', '')),
                    'views': str(row.get('Views', '')),
                    'replies': str(row.get('Replies', '')),
                    'reposts': str(row.get('Reposts', '')),
                    'likes': str(row.get('Likes', '')),
                    'profile_followers': str(row.get('Profile Followers', '')),
                    'url': str(row.get('URL', '')),
                    'images': row.get('Images', '').split(', ') if pd.notna(row.get('Images', '')) and row.get('Images', '') else []
                }
                tweets.append(tweet)
                if tweet['id']:
                    seen_ids.add(tweet['id'])
            
            return tweets, seen_ids
    except Exception as e:
        print(f"Warning: Could not load existing Excel file: {e}")
    return [], set()

def save_tweets_to_excel(tweets, filepath):
    """Save tweets to Excel file."""
    if not EXCEL_SUPPORT:
        print("Warning: pandas/openpyxl not installed. Cannot save to Excel. Install with: pip install pandas openpyxl")
        return False
    
    try:
        # Prepare data for Excel - flatten the structure (excluding link and text fields)
        excel_data = []
        for tweet in tweets:
            row = {
                'ID': tweet.get('id', ''),
                'Author': tweet.get('author', ''),
                'Username': tweet.get('username', ''),
                'Display Name': tweet.get('display_name', ''),
                'Body': tweet.get('body', ''),
                'Date': tweet.get('date', ''),
                'Views': tweet.get('views', ''),
                'Replies': tweet.get('replies', ''),
                'Reposts': tweet.get('reposts', ''),
                'Likes': tweet.get('likes', ''),
                'Profile Followers': tweet.get('profile_followers', ''),
                'URL': tweet.get('url', ''),
                'Images': ', '.join(tweet.get('images', [])) if isinstance(tweet.get('images'), list) else str(tweet.get('images', ''))
            }
            excel_data.append(row)
        
        df = pd.DataFrame(excel_data)
        df.to_excel(filepath, index=False, engine='openpyxl')
        return True
    except Exception as e:
        print(f"Warning: Could not save to Excel: {e}")
        return False

# Define the path for the browser profile directory
BROWSER_PROFILE_PATH = "browser_profile"

def random_sleep_async(min_sec=1, max_sec=3):
    """Asynchronous sleep for a random duration."""
    return asyncio.sleep(random.uniform(min_sec, max_sec))

def _parse_engagement_number(text):
    """
    Parse engagement numbers from text like "10K", "1.2M", "500", etc.
    Returns the number as a string in the same format (e.g., "10K", "1.2M")
    """
    if not text:
        return None
    
    # Remove commas and whitespace
    text = text.strip().replace(',', '')
    
    # Try to extract number with optional K/M/B suffix
    match = re.search(r'([\d.]+)\s*([KMBkmb]?)\s*', text)
    if match:
        number = match.group(1)
        suffix = match.group(2).upper() if match.group(2) else ''
        return f"{number}{suffix}" if suffix else number
    
    # If no match, try to extract just numbers
    numbers = re.findall(r'\d+', text)
    if numbers:
        return numbers[0]
    
    return None

async def scrape_search_results(
    keyword: str = None,
    from_account: str = None, # Username to get tweets from (e.g., "elonmusk" for @elonmusk)
    username: str = None, # Optional - only needed if profile doesn't exist or login fails
    password: str = None, # Optional - only needed if profile doesn't exist or login fails
    email: str = None, # Optional email for verification
    since_date: str = None, # Since date in YYYY-MM-DD format
    until_date: str = None, # Until date in YYYY-MM-DD format
    limit: int = None, # Max number of tweets to collect
    latest: bool = False, # If True, get latest tweets from last 24 hours with f=live
    output_file: str = None, # Output file path to save tweets incrementally
    app_instance=None # Pass the main application instance to emit signals (used in GUI, None in CLI)
):
    """
    Scrapes tweets from x.com search results using Playwright with persistent browser profile.

    Args:
        keyword: The search term (optional if from_account is provided).
        from_account: Username to get tweets from (e.g., "elonmusk" for @elonmusk). Optional if keyword is provided.
        username: Twitter username (optional if browser profile exists and is logged in).
        password: Twitter password (optional if browser profile exists and is logged in).
        email: Optional email for verification steps.
        since_date: The start date for filtering (YYYY-MM-DD).
        until_date: The end date for filtering (YYYY-MM-DD).
        limit: The maximum number of tweets to collect.
        latest: If True, get latest tweets from last 24 hours using f=live parameter.
        output_file: Path to JSON file to save tweets incrementally as they're collected.
        app_instance: The main PyQt application instance to emit signals.
    """
    # Validate that either keyword or from_account is provided
    if not keyword and not from_account:
        raise ValueError("Either 'keyword' or 'from_account' must be provided")
    # If latest is True, automatically set since_date to 24 hours ago
    # This ensures we stop when tweets older than 24 hours appear
    if latest:
        since_date_24h_ago = (datetime.now() - timedelta(hours=24)).strftime('%Y-%m-%d')
        if not since_date:  # Only override if since_date not explicitly provided
            since_date = since_date_24h_ago
            print(f"Latest mode: Using f=live parameter. Will filter tweets from last 24 hours (since {since_date}).")
        else:
            print(f"Latest mode: Using f=live parameter. Will filter by provided date range.")
    
    all_collected_tweets = [] # Keep a list internally to pass to the finished signal
    seen_tweet_ids = set()
    
    # Initialize output file if provided
    if output_file:
        # Check if it's an Excel file
        if is_excel_file(output_file):
            if os.path.exists(output_file):
                existing_tweets, seen_tweet_ids = load_existing_tweets_from_excel(output_file)
                all_collected_tweets = existing_tweets
                print(f"Loaded {len(existing_tweets)} existing tweets from {output_file}")
            else:
                # Create empty Excel file
                save_tweets_to_excel([], output_file)
                all_collected_tweets = []
                print(f"Created new output file: {output_file}")
        else:
            # JSON file handling
            if os.path.exists(output_file):
                try:
                    with open(output_file, 'r', encoding='utf-8') as f:
                        existing_tweets = json.load(f)
                        if isinstance(existing_tweets, list):
                            all_collected_tweets = existing_tweets
                            seen_tweet_ids = {tweet.get('id') for tweet in existing_tweets if tweet.get('id')}
                            print(f"Loaded {len(existing_tweets)} existing tweets from {output_file}")
                except (json.JSONDecodeError, FileNotFoundError):
                    # If file is corrupted or doesn't exist, start fresh
                    all_collected_tweets = []
            else:
                # Create empty file with empty array
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump([], f, indent=4, ensure_ascii=False)
                print(f"Created new output file: {output_file}")

    async with async_playwright() as p:
        browser = None # Initialize browser to None
        try:
            # Launch browser with persistent context (browser profile)
            # This will automatically load saved cookies and session data
            print(f"Launching browser with profile: {BROWSER_PROFILE_PATH}")
            
            # Check for lockfile and warn if profile might be in use
            lockfile_path = os.path.join(BROWSER_PROFILE_PATH, "lockfile")
            if os.path.exists(lockfile_path):
                print("WARNING: Browser profile lockfile exists. Another browser instance might be using this profile.")
                print("If you have Chrome/Chromium open, please close it and try again.")
            
            browser = await p.chromium.launch_persistent_context(
                user_data_dir=BROWSER_PROFILE_PATH,
                headless=False,  # Always use headful mode (visible browser)
                slow_mo=100,
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
            # Wait a moment for browser to fully initialize
            await asyncio.sleep(0.5)
            
            pages = browser.pages
            if pages:
                page = pages[0]
            else:
                page = await browser.new_page()
            
            print("Browser initialized successfully")

            # Enhanced anti-detection script
            await page.add_init_script("""
                // Remove webdriver property
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                // Override plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                
                // Override languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
                
                // Add chrome object
                window.chrome = {
                    runtime: {}
                };
                
                // Override permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
                
                // Override getBattery
                if (navigator.getBattery) {
                    navigator.getBattery = () => Promise.resolve({
                        charging: true,
                        chargingTime: 0,
                        dischargingTime: Infinity,
                        level: 1
                    });
                }
                
                // Override webdriver in window
                Object.defineProperty(window, 'navigator', {
                    value: new Proxy(navigator, {
                        has: (target, key) => (key === 'webdriver' ? false : key in target),
                        get: (target, key) => (key === 'webdriver' ? undefined : target[key])
                    })
                });
            """)

            # Use saved browser profile - proceed directly to search
            # The persistent context automatically loads cookies, so we can go straight to search
            print("Using saved browser profile. Proceeding to search...")
            
            # Proceed to search and scrape
            await _perform_search_and_scrape(
                page, keyword, from_account, since_date, until_date, limit, latest, output_file,
                all_collected_tweets, seen_tweet_ids, app_instance
            )
            return all_collected_tweets

        except Exception as e:
            print(f"An error occurred: {e}")
            if app_instance: app_instance.error.emit(f"An error occurred: {e}")
            # Return current collected tweets on error
            return all_collected_tweets

        finally:
            if browser:
                await browser.close()
                print("Browser closed.")

    return all_collected_tweets # Should be covered by returns in try/except blocks, but here as fallback

# Helper function for performing search and scraping
async def _perform_search_and_scrape(
     page,
     keyword,
     from_account,
     since_date,
     until_date,
     limit,
     latest,
     output_file,
     all_collected_tweets, # Pass lists/sets to be modified in place
     seen_tweet_ids,
     app_instance
    ):
    
    def save_tweet_incremental(tweet_info):
        """Save a single tweet to the output file incrementally."""
        if not output_file:
            return
        
        try:
            # Check if it's an Excel file
            if is_excel_file(output_file):
                # For Excel, we need to read all existing tweets, add new one, and rewrite
                if os.path.exists(output_file):
                    existing_tweets, _ = load_existing_tweets_from_excel(output_file)
                    tweets = existing_tweets
                else:
                    tweets = []
                
                # Append new tweet
                tweets.append(tweet_info)
                
                # Save to Excel
                save_tweets_to_excel(tweets, output_file)
            else:
                # JSON file handling
                if os.path.exists(output_file):
                    with open(output_file, 'r', encoding='utf-8') as f:
                        tweets = json.load(f)
                        if not isinstance(tweets, list):
                            tweets = []
                else:
                    tweets = []
                
                # Append new tweet
                tweets.append(tweet_info)
                
                # Write back to file
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(tweets, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Could not save tweet incrementally: {e}")

    # Helper function to extract account names from keywords and create exclusions
    def extract_account_exclusions(keyword_str):
        """Extract potential account names from keywords and create exclusion list.
        Works for both single keywords and multiple keywords (OR queries).
        For 'PokerStars' or 'PokerStars OR pokerstars', extracts 'pokerstars' and 'PokerStars' for exclusion.
        """
        exclusions = []
        # Check if keyword contains OR (multiple keywords)
        if ' OR ' in keyword_str.upper():
            # Extract keywords from OR query: (keyword1) OR (keyword2) OR (keyword3)
            import re
            # Match patterns like (keyword) in the OR query
            matches = re.findall(r'\(([^)]+)\)', keyword_str)
            for match in matches:
                kw = match.strip()
                # Remove @ if present
                account_name = kw.lstrip('@').strip()
                if account_name:
                    # Add both lowercase and original case variants if different
                    exclusions.append(account_name.lower())
                    if account_name.lower() != account_name:
                        exclusions.append(account_name)
        else:
            # Single keyword - extract account name variants
            kw = keyword_str.strip().lstrip('@').strip()
            if kw:
                # Add both lowercase and original case variants
                exclusions.append(kw.lower())
                if kw.lower() != kw:
                    exclusions.append(kw)
        
        # Remove duplicates while preserving order (case-insensitive)
        seen = set()
        unique_exclusions = []
        for exc in exclusions:
            exc_lower = exc.lower()
            if exc_lower not in seen:
                seen.add(exc_lower)
                unique_exclusions.append(exc)
        
        return unique_exclusions
    
    # Construct search query based on keyword or from_account
    if from_account:
        # Remove @ if user included it
        account_name = from_account.lstrip('@')
        # For account-based search with keywords: (keyword1 OR keyword2) -@account1 -@account2
        if keyword:
            # Extract account exclusions from keyword
            account_exclusions = extract_account_exclusions(keyword)
            # Add the from_account to exclusions (both cases)
            account_exclusions.append(account_name.lower())
            if account_name.lower() != account_name:
                account_exclusions.append(account_name)
            
            # Remove duplicates
            seen = set()
            unique_exclusions = []
            for exc in account_exclusions:
                exc_lower = exc.lower()
                if exc_lower not in seen:
                    seen.add(exc_lower)
                    unique_exclusions.append(exc)
            
            # Build exclusion string: -@account1 -@account2
            exclusion_str = " ".join(f"-@{acc}" for acc in unique_exclusions)
            search_query = f"{keyword} {exclusion_str}"
            print(f"Searching for keyword: {keyword} (excluding accounts: {', '.join(unique_exclusions)})")
        else:
            # Pure account-based search: use (from:username) format
            search_query = f"(from:{account_name})"
            print(f"Searching for tweets from account: @{account_name}")
    else:
        # Keyword search - automatically exclude @ account variants for ALL keywords (single or multiple)
        # Extract and add account exclusions
        account_exclusions = extract_account_exclusions(keyword)
        if account_exclusions:
            # Build exclusion string: -@account1 -@account2
            exclusion_str = " ".join(f"-@{acc}" for acc in account_exclusions)
            search_query = f"{keyword} {exclusion_str}"
            print(f"Searching for keyword: {keyword}")
            print(f"Automatically excluding accounts: {', '.join(account_exclusions)}")
        else:
            # No exclusions found (shouldn't happen normally, but handle edge case)
            search_query = keyword
            print(f"Searching for keyword: {keyword}")
    
    # Build the complete search query with date filters if provided
    complete_query = search_query
    if until_date:
        complete_query += f" until:{until_date}"
    if since_date:
        complete_query += f" since:{since_date}"
    
    # Properly URL-encode the complete search query
    encoded_query = urllib.parse.quote(complete_query)
    search_url = f"https://x.com/search?q={encoded_query}"

    # Add f=live parameter for latest tweets (date filters are already in the query)
    if latest:
        search_url += "&src=typed_query&f=live"
    else:
        search_url += "&src=typed_query"
    
    print(f"Search URL: {search_url}")

    # print(f"Navigating to search URL: {search_url}")
    # Navigate to search URL with optimized loading
    await page.goto(search_url, timeout=60000, wait_until='domcontentloaded')
    await asyncio.sleep(0.3)  # Minimal wait for initial load
    
    # Check if we're on the right page or if we got blocked/redirected
    current_url = page.url
    print(f"Current URL: {current_url}")
    
    # Check if redirected to login or authentication page
    login_indicators = ["login", "i/flow", "account/access", "authenticate", "signin"]
    if any(indicator in current_url.lower() for indicator in login_indicators):
        print("\n" + "="*60)
        print("ERROR: Session expired - X.com is asking for login")
        print("="*60)
        print("Your browser profile session has expired or been invalidated.")
        print("This can happen if:")
        print("  - The session was created too long ago")
        print("  - X.com detected suspicious activity")
        print("  - You logged out from another device")
        print("\nSOLUTION: Re-run the login script to refresh your session:")
        print("  python login_and_save_profile.py")
        print("="*60 + "\n")
        return
    
    # Also check page content for login prompts
    try:
        page_text = await page.evaluate("() => document.body.innerText || ''")
        if "sign in" in page_text.lower() or "log in" in page_text.lower() or "enter your phone" in page_text.lower():
            if "search" not in page_text.lower()[:500]:  # Make sure it's not just a search page with login button
                print("\n" + "="*60)
                print("ERROR: Login page detected in content")
                print("="*60)
                print("X.com is showing a login page. Please re-authenticate:")
                print("  python login_and_save_profile.py")
                print("="*60 + "\n")
                return
    except:
        pass
    
    # Verify cookies are loaded (check after navigation)
    try:
        cookies = await page.context.cookies()
        x_cookies = [c for c in cookies if 'x.com' in c.get('domain', '') or 'twitter.com' in c.get('domain', '')]
        if x_cookies:
            print(f"Session active: {len(x_cookies)} X.com cookies found")
        else:
            print("WARNING: No X.com cookies found - may need to re-login")
    except:
        pass
    
    # print("Waiting for search results...")
    try:
        await page.wait_for_selector('article', timeout=80000)
        # print("Search results loaded, first tweet element (article) found.")
    except Exception as e:
        print(f"Timeout waiting for search results. No tweets found or page structure changed: {e}")
        
        # Try to get more diagnostic info
        try:
            body_text = await page.evaluate("() => document.body.innerText")
            if "login" in body_text.lower() or "sign in" in body_text.lower():
                print("ERROR: Appears to be redirected to login page. Browser profile may have expired.")
            elif "rate limit" in body_text.lower() or "too many requests" in body_text.lower():
                print("ERROR: Rate limited by X.com. Please wait before trying again.")
            else:
                print(f"Page body preview: {body_text[:500]}")
        except:
            pass
        if app_instance: app_instance.error.emit("Timeout waiting for search results.")
        return # Exit if results don't load

    print("Starting to scroll and extract tweets...")
    last_height = await page.evaluate("document.body.scrollHeight")
    collected_count = 0
    scroll_attempts_without_new_tweets = 0
    MAX_SCROLL_ATTEMPTS_WITHOUT_NEW_TWEETS = 3 # Stop after 3 scrolls find no new tweets (reduced from 5 for faster stopping)
    tweets_outside_date_range = 0  # Track consecutive tweets outside date range
    MAX_TWEETS_OUTSIDE_RANGE = 10  # Stop if we see 10 consecutive tweets outside date range
    
    # Cache for follower count when doing account-based search (all tweets from same account)
    cached_follower_count = None
    account_followers_fetched = False
    
    # Cache for follower counts per username (for keyword searches to avoid re-fetching)
    follower_count_cache = {}  # {username: follower_count}
    
    # For account-based searches, fetch follower count once before the loop
    if from_account:
        account_name = from_account.lstrip('@')
        print(f"Fetching follower count for @{account_name} (will be reused for all tweets)...")
        try:
            context = page.context
            profile_url = f"https://x.com/{account_name}"
            new_page = await context.new_page()
            
            try:
                await new_page.goto(profile_url, timeout=30000, wait_until='domcontentloaded')
                await asyncio.sleep(0.5)  # Short wait for page to load
                
                # Wait for profile stats to load (with shorter timeout)
                try:
                    await new_page.wait_for_selector('a[href*="/followers"]', timeout=2000)
                except:
                    pass  # Continue even if selector doesn't appear
                
                # Method 1: Look for link with /followers in href (most reliable)
                try:
                    follower_links = await new_page.query_selector_all('a[href*="/followers"]')
                    for follower_link in follower_links:
                        try:
                            link_text = await follower_link.inner_text()
                            # Look for pattern like "229.8M Followers" or "1,234 Followers"
                            follower_match = re.search(r'([\d,.]+[KMBkmb]?)\s*followers?', link_text, re.IGNORECASE)
                            if follower_match:
                                cached_follower_count = _parse_engagement_number(follower_match.group(1))
                                break
                        except:
                            continue
                except:
                    pass
                
                # Method 2: Look for span elements containing follower text
                if cached_follower_count is None:
                    try:
                        all_spans = await new_page.query_selector_all('span')
                        for span in all_spans:
                            try:
                                text = await span.inner_text()
                                if 'followers' in text.lower() and 'following' not in text.lower():
                                    follower_match = re.search(r'([\d,.]+[KMBkmb]?)\s*followers?', text, re.IGNORECASE)
                                    if follower_match:
                                        cached_follower_count = _parse_engagement_number(follower_match.group(1))
                                        break
                            except:
                                continue
                    except:
                        pass
                
                # Method 3: Look for data-testid attributes
                if cached_follower_count is None:
                    try:
                        follower_elems = await new_page.query_selector_all('[data-testid*="follower"], [data-testid*="Follower"]')
                        for elem in follower_elems:
                            try:
                                text = await elem.inner_text()
                                aria_label = await elem.get_attribute('aria-label') or ''
                                combined = f"{text} {aria_label}"
                                follower_match = re.search(r'([\d,.]+[KMBkmb]?)\s*followers?', combined, re.IGNORECASE)
                                if follower_match:
                                    cached_follower_count = _parse_engagement_number(follower_match.group(1))
                                    break
                            except:
                                continue
                    except:
                        pass
                
                # Method 4: Use JavaScript to find follower count in the page
                if cached_follower_count is None:
                    try:
                        follower_count_js = await new_page.evaluate("""
                            () => {
                                // Look for links with /followers
                                const followerLinks = Array.from(document.querySelectorAll('a[href*="/followers"]'));
                                for (const link of followerLinks) {
                                    const text = link.innerText || link.textContent || '';
                                    const match = text.match(/([\\d,.]+[KMBkmb]?)\\s*followers?/i);
                                    if (match) return match[1];
                                }
                                
                                // Look in all spans
                                const spans = Array.from(document.querySelectorAll('span'));
                                for (const span of spans) {
                                    const text = span.innerText || span.textContent || '';
                                    if (text.toLowerCase().includes('followers') && !text.toLowerCase().includes('following')) {
                                        const match = text.match(/([\\d,.]+[KMBkmb]?)\\s*followers?/i);
                                        if (match) return match[1];
                                    }
                                }
                                
                                // Search all text
                                const bodyText = document.body.innerText || document.body.textContent || '';
                                const matches = bodyText.match(/([\\d,.]+[KMBkmb]?)\\s*followers?/gi);
                                if (matches && matches.length > 0) {
                                    return matches[0].replace(/\\s*followers?/gi, '').trim();
                                }
                                
                                return null;
                            }
                        """)
                        if follower_count_js:
                            cached_follower_count = _parse_engagement_number(follower_count_js)
                    except:
                        pass
                
                if cached_follower_count:
                    account_followers_fetched = True
                    print(f"Cached follower count for @{account_name}: {cached_follower_count}")
                else:
                    print(f"Warning: Could not fetch follower count for @{account_name}, will skip for all tweets")
                    account_followers_fetched = True  # Mark as fetched even if failed to avoid retrying
                
                await new_page.close()
                
            except Exception as e:
                print(f"Error fetching follower count: {e}")
                account_followers_fetched = True  # Mark as fetched to avoid retrying
                try:
                    await new_page.close()
                except:
                    pass
        except Exception as e:
            print(f"Error setting up follower count fetch: {e}")
            account_followers_fetched = True  # Mark as fetched to avoid retrying
    
    # Parse date filters for comparison
    since_date_obj = None
    until_date_obj = None
    if since_date:
        try:
            since_date_obj = datetime.strptime(since_date, '%Y-%m-%d')
        except:
            pass
    if until_date:
        try:
            until_date_obj = datetime.strptime(until_date, '%Y-%m-%d')
        except:
            pass

    while (limit is None or collected_count < limit) and scroll_attempts_without_new_tweets < MAX_SCROLL_ATTEMPTS_WITHOUT_NEW_TWEETS and tweets_outside_date_range < MAX_TWEETS_OUTSIDE_RANGE:
        # Check if we're still on the search results page (not navigated to individual posts)
        current_url = page.url
        if '/search' not in current_url:
            print(f"WARNING: Navigated away from search page to: {current_url}")
            print("Navigating back to search results...")
            await page.goto(search_url, timeout=30000, wait_until='domcontentloaded')
            await asyncio.sleep(1.5)  # Wait for page to reload
            # Re-wait for articles to load
            try:
                await page.wait_for_selector('article', timeout=10000)
            except:
                pass
            continue  # Skip this iteration and try again
        
        tweet_elements = await page.query_selector_all('article')
        # print(f"Found {len(tweet_elements)} article elements on current view.")

        newly_collected_in_scroll = 0  # Counter for tweets actually collected and saved in this scroll
        current_tweet_ids = set() # To track tweets found in the current scroll window

        for tweet_element in tweet_elements:
            if limit is not None and collected_count >= limit:
                break

            try:
                tweet_link_element = await tweet_element.query_selector("a[href*='/status/']")
                tweet_url = await tweet_link_element.get_attribute('href') if tweet_link_element else None
                tweet_id = tweet_url.split('/')[-1] if tweet_url else None
                tweet_link = f"https://x.com{tweet_url}" if tweet_url else None

                if tweet_id:
                     current_tweet_ids.add(tweet_id) # Add to set of tweets seen in this scroll window

                # Only process if we have a valid, unseen tweet ID
                if tweet_id and tweet_id not in seen_tweet_ids:

                    # *** Handle 'Show more' button before text extraction ***
                    # Skip clicking "Show more" to avoid potential navigation - just extract what's visible
                    # If text is truncated, we'll get what's available without expanding
                    pass

                    # *** Extract Tweet Text (after potential expansion) ***
                    text_element = await tweet_element.query_selector('[data-testid="tweetText"]')
                    raw_text = await text_element.inner_text() if text_element else "Could not retrieve tweet text."

                    # *** Extract Username ***
                    username = None
                    username_link_element = await tweet_element.query_selector('a[role="link"][href^="/"]')
                    if username_link_element:
                         href = await username_link_element.get_attribute('href')
                         if href and href.startswith('/'):
                              username = href.lstrip('/')
                    
                    # For account-based searches, skip tweets that are not from the target account
                    # This prevents scraping replies and thread content
                    if from_account:
                        account_name = from_account.lstrip('@').lower()
                        if username and username.lower() != account_name:
                            # Skip this tweet - it's not from the target account (likely a reply or thread content)
                            continue

                    # *** Extract Display Name ***
                    display_name = None
                    user_names_container = await tweet_element.query_selector('[data-testid="User-Name"]')
                    if user_names_container:
                         full_names_text = await user_names_container.inner_text()
                         if full_names_text:
                             display_name_candidates = full_names_text.strip().split('\n')
                             if display_name_candidates:
                                 display_name = display_name_candidates[0].strip()
                                 if username and display_name.endswith(f' @{username}'):
                                     display_name = display_name[:-len(f' @{username}')].strip()
                                 elif username and display_name.endswith(username):
                                      display_name = display_name[:-len(username)].strip()

                    # *** Extract Tweet Images ***
                    image_elements = await tweet_element.query_selector_all('img[src^="https://pbs.twimg.com/"]')
                    image_urls = [await img.get_attribute('src') for img in image_elements if await img.get_attribute('src')]

                    # *** Extract Tweet Date ***
                    date_element = await tweet_element.query_selector('time')
                    tweet_date_str = None
                    if date_element:
                        datetime_attr = await date_element.get_attribute('datetime')
                        if datetime_attr:
                            try:
                                dt_object = datetime.fromisoformat(datetime_attr.replace('Z', '+00:00'))
                                tweet_date_str = dt_object.isoformat()
                            except ValueError:
                                pass # Continue to inner text parsing

                        if tweet_date_str is None:
                            inner_text = await date_element.inner_text()
                            if inner_text:
                                cleaned_text = inner_text.strip()
                                date_match = re.search(
                                    r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}(?:,\s+\d{4})?'
                                    r'|\d{4}/\d{2}/\d{2}'
                                    r'|\d{2}/\d{2}/\d{4}'
                                    r'|\d{1,2}:\d{2}\s*(?:AM|PM)?',
                                    cleaned_text
                                )

                                if date_match:
                                    date_part = date_match.group(0).strip()
                                    date_formats = [
                                        '%b %d',      # e.g., May 20
                                        '%b %d, %Y',  # e.g., May 20, 2023
                                        '%H:%M %p',   # e.g., 10:30 AM
                                        '%I:%M %p',   # e.g., 10:30 AM
                                        '%Y/%m/%d', # e.g., 2023/12/31
                                        '%m/%d/%Y', # e.g., 12/31/2023
                                        '%H:%M',
                                        '%I:%M',
                                    ]
                                    current_year = datetime.now().year
                                    parsed_date = None
                                    for fmt in date_formats:
                                        try:
                                            if '%b %d' in fmt and re.match(r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}', date_part):
                                                dt_obj = datetime.strptime(f'{date_part} {current_year}', f'{fmt} %Y')
                                                parsed_date = dt_obj
                                                break
                                            elif '%H' in fmt or '%I' in fmt:
                                                 dt_obj = datetime.strptime(date_part, fmt).replace(year=datetime.now().year, month=datetime.now().month, day=datetime.now().day)
                                                 parsed_date = dt_obj
                                                 break
                                            else:
                                                 dt_obj = datetime.strptime(date_part, fmt)
                                                 parsed_date = dt_obj
                                                 break
                                        except ValueError:
                                            pass

                                    if parsed_date:
                                        tweet_date_str = parsed_date.isoformat()
                                    else:
                                         tweet_date_str = date_part
                                else:
                                     tweet_date_str = cleaned_text

                    if tweet_date_str is None:
                         tweet_date_str = "Date not found"
                    
                    # *** Check if tweet is outside date range (for latest mode filtering) ***
                    tweet_date_obj = None
                    is_outside_range = False
                    if tweet_date_str and tweet_date_str != "Date not found":
                        try:
                            # Try to parse the date string
                            if 'T' in tweet_date_str or '+' in tweet_date_str:
                                # ISO format
                                tweet_date_obj = datetime.fromisoformat(tweet_date_str.replace('Z', '+00:00').split('+')[0])
                            else:
                                # Try other formats
                                for fmt in ['%Y-%m-%d', '%b %d, %Y', '%Y/%m/%d', '%m/%d/%Y']:
                                    try:
                                        tweet_date_obj = datetime.strptime(tweet_date_str.split('T')[0], fmt)
                                        break
                                    except:
                                        continue
                            
                            # Check if tweet is outside date range
                            if tweet_date_obj:
                                if since_date_obj and tweet_date_obj.date() < since_date_obj.date():
                                    is_outside_range = True
                                if until_date_obj and tweet_date_obj.date() > until_date_obj.date():
                                    is_outside_range = True
                        except:
                            pass  # If date parsing fails, continue anyway

                    # *** Extract Engagement Metrics (Views, Replies, Reposts, Likes) ***
                    views = None
                    replies = None
                    reposts = None
                    likes = None
                    
                    # Try to find engagement buttons/links using multiple methods
                    try:
                        # Method 1: Look for aria-label attributes (most reliable)
                        engagement_elements = await tweet_element.query_selector_all('[aria-label]')
                        for elem in engagement_elements:
                            aria_label = await elem.get_attribute('aria-label')
                            if aria_label:
                                aria_lower = aria_label.lower()
                                # Extract numbers from aria-label like "1,234 replies" or "10.5K likes"
                                if 'reply' in aria_lower or 'replied' in aria_lower:
                                    num_match = re.search(r'([\d,.]+[KMBkmb]?)\s*(?:replies?|replied)', aria_lower, re.IGNORECASE)
                                    if num_match and replies is None:
                                        replies = _parse_engagement_number(num_match.group(1))
                                elif 'repost' in aria_lower or 'retweet' in aria_lower:
                                    num_match = re.search(r'([\d,.]+[KMBkmb]?)\s*(?:reposts?|retweets?)', aria_lower, re.IGNORECASE)
                                    if num_match and reposts is None:
                                        reposts = _parse_engagement_number(num_match.group(1))
                                elif 'like' in aria_lower or 'liked' in aria_lower:
                                    num_match = re.search(r'([\d,.]+[KMBkmb]?)\s*(?:likes?|liked)', aria_lower, re.IGNORECASE)
                                    if num_match and likes is None:
                                        likes = _parse_engagement_number(num_match.group(1))
                                elif 'view' in aria_lower:
                                    num_match = re.search(r'([\d,.]+[KMBkmb]?)\s*views?', aria_lower, re.IGNORECASE)
                                    if num_match and views is None:
                                        views = _parse_engagement_number(num_match.group(1))
                        
                        # Method 2: Look for data-testid buttons and get their text
                        if replies is None:
                            reply_element = await tweet_element.query_selector('[data-testid="reply"]')
                            if reply_element:
                                reply_text = await reply_element.inner_text()
                                replies = _parse_engagement_number(reply_text)
                        
                        if reposts is None:
                            retweet_element = await tweet_element.query_selector('[data-testid="retweet"]')
                            if retweet_element:
                                retweet_text = await retweet_element.inner_text()
                                reposts = _parse_engagement_number(retweet_text)
                        
                        if likes is None:
                            like_element = await tweet_element.query_selector('[data-testid="like"]')
                            if like_element:
                                like_text = await like_element.inner_text()
                                likes = _parse_engagement_number(like_text)
                        
                        # Method 3: Look for views in text content (views might be displayed differently)
                        if views is None:
                            # Look for elements containing "views" text
                            all_text_elements = await tweet_element.query_selector_all('span, div, a')
                            for elem in all_text_elements:
                                text = await elem.inner_text()
                                if text:
                                    view_match = re.search(r'([\d,.]+[KMBkmb]?)\s*views?', text, re.IGNORECASE)
                                    if view_match:
                                        views = _parse_engagement_number(view_match.group(1))
                                        break
                    except Exception as e:
                        # print(f"Error extracting engagement metrics: {e}")
                        pass
                    
                    # *** Extract Profile Followers ***
                    # For account-based searches, use cached value. For keyword searches, fetch for each unique account.
                    profile_followers = None
                    
                    # If doing account-based search, use cached value (fetched before loop)
                    if from_account and account_followers_fetched:
                        profile_followers = cached_follower_count
                    elif not from_account and username:
                        # For keyword-based search, check cache first, then fetch if not cached
                        if username in follower_count_cache:
                            profile_followers = follower_count_cache[username]
                        else:
                            # Fetch follower count for this unique account
                            try:
                                context = page.context
                                profile_url = f"https://x.com/{username}"
                                new_page = await context.new_page()
                                
                                try:
                                    await new_page.goto(profile_url, timeout=30000, wait_until='domcontentloaded')
                                    await asyncio.sleep(0.5)  # Short wait for page to load
                                    
                                    # Wait for follower link to appear
                                    try:
                                        await new_page.wait_for_selector('a[href*="/followers"]', timeout=2000)
                                    except:
                                        pass
                                    
                                    # Method 1: Look for link with /followers in href
                                    try:
                                        follower_links = await new_page.query_selector_all('a[href*="/followers"]')
                                        for follower_link in follower_links:
                                            try:
                                                link_text = await follower_link.inner_text()
                                                follower_match = re.search(r'([\d,.]+[KMBkmb]?)\s*followers?', link_text, re.IGNORECASE)
                                                if follower_match:
                                                    profile_followers = _parse_engagement_number(follower_match.group(1))
                                                    break
                                            except:
                                                continue
                                    except:
                                        pass
                                    
                                    # Method 2: Look for span elements
                                    if profile_followers is None:
                                        try:
                                            all_spans = await new_page.query_selector_all('span')
                                            for span in all_spans:
                                                try:
                                                    text = await span.inner_text()
                                                    if 'followers' in text.lower() and 'following' not in text.lower():
                                                        follower_match = re.search(r'([\d,.]+[KMBkmb]?)\s*followers?', text, re.IGNORECASE)
                                                        if follower_match:
                                                            profile_followers = _parse_engagement_number(follower_match.group(1))
                                                            break
                                                except:
                                                    continue
                                        except:
                                            pass
                                    
                                    # Method 3: Use JavaScript extraction
                                    if profile_followers is None:
                                        try:
                                            follower_count_js = await new_page.evaluate("""
                                                () => {
                                                    const followerLinks = Array.from(document.querySelectorAll('a[href*="/followers"]'));
                                                    for (const link of followerLinks) {
                                                        const text = link.innerText || link.textContent || '';
                                                        const match = text.match(/([\\d,.]+[KMBkmb]?)\\s*followers?/i);
                                                        if (match) return match[1];
                                                    }
                                                    const bodyText = document.body.innerText || '';
                                                    const matches = bodyText.match(/([\\d,.]+[KMBkmb]?)\\s*followers?/gi);
                                                    if (matches && matches.length > 0) {
                                                        return matches[0].replace(/\\s*followers?/gi, '').trim();
                                                    }
                                                    return null;
                                                }
                                            """)
                                            if follower_count_js:
                                                profile_followers = _parse_engagement_number(follower_count_js)
                                        except:
                                            pass
                                    
                                    # Cache the follower count for this username
                                    if profile_followers:
                                        follower_count_cache[username] = profile_followers
                                    
                                    await new_page.close()
                                    
                                except Exception as profile_error:
                                    try:
                                        await new_page.close()
                                    except:
                                        pass
                                    
                            except Exception as e:
                                pass

                    # *** Add collected tweet and update counts ONLY for unique tweets ***
                    tweet_info = {
                        'id': tweet_id,
                        'views': views or "N/A",
                        'replies': replies or "N/A",
                        'reposts': reposts or "N/A",
                        'likes': likes or "N/A",
                        'body': raw_text,
                        'url': tweet_link,
                        'date': tweet_date_str,
                        'author': username or display_name or "N/A",
                        'profile_followers': profile_followers or "N/A",
                        # Keep old fields for backward compatibility
                        'link': tweet_link,
                        'username': username,
                        'display_name': display_name,
                        'text': raw_text,
                        'images': image_urls,
                    }

                    # Check if tweet should be added (within date range or no date filtering)
                    should_add_tweet = True
                    if is_outside_range and (since_date_obj is not None or until_date_obj is not None):
                        should_add_tweet = False
                        tweets_outside_date_range += 1
                        # In latest mode or when date filtering is active, if we've scrolled past since_date, stop immediately
                        if since_date_obj and tweet_date_obj and tweet_date_obj.date() < since_date_obj.date():
                            print(f"Reached tweets older than {since_date}. Stopping scroll.")
                            break
                        # Stop immediately when we find tweets outside the date range (for latest mode)
                        if latest and is_outside_range:
                            print(f"Found tweet outside date range ({tweet_date_obj.date() if tweet_date_obj else 'unknown'}). Stopping scroll.")
                            break
                        # Also stop if we see too many consecutive tweets outside range (for non-latest mode)
                        if not latest and tweets_outside_date_range >= MAX_TWEETS_OUTSIDE_RANGE:
                            print(f"Stopping: Found {tweets_outside_date_range} consecutive tweets outside date range.")
                            break
                    else:
                        # Reset counter if we found a tweet in range
                        tweets_outside_date_range = 0
                    
                    if should_add_tweet:
                        all_collected_tweets.append(tweet_info)
                        seen_tweet_ids.add(tweet_id)
                        newly_collected_in_scroll += 1
                        collected_count += 1
                        
                        # Save tweet incrementally to file
                        save_tweet_incremental(tweet_info)
                        
                        # Check URL after saving each tweet to catch navigation
                        check_url = page.url
                        if '/search' not in check_url:
                            print(f"WARNING: Navigated away during extraction to: {check_url}")
                            print("Navigating back to search results...")
                            await page.goto(search_url, timeout=30000, wait_until='domcontentloaded')
                            await asyncio.sleep(1.5)
                            try:
                                await page.wait_for_selector('article', timeout=10000)
                            except:
                                pass
                            break  # Break out of tweet loop and restart

                    # Print collected tweet information to the console in a user-friendly format
                    if app_instance is None: # Only print in CLI mode
                        print("--------------------")
                        print(f"ID: {tweet_info.get('id', 'N/A')}")
                        print(f"Views: {tweet_info.get('views', 'N/A')}")
                        print(f"Replies: {tweet_info.get('replies', 'N/A')}")
                        print(f"Reposts: {tweet_info.get('reposts', 'N/A')}")
                        print(f"Likes: {tweet_info.get('likes', 'N/A')}")
                        print(f"Author: {tweet_info.get('author', 'N/A')}")
                        print(f"Profile Followers: {tweet_info.get('profile_followers', 'N/A')}")
                        print(f"Date: {tweet_info.get('date', 'N/A')}")
                        print(f"URL: {tweet_info.get('url', 'N/A')}")
                        print(f"Body:\n{tweet_info.get('body', 'Could not retrieve text.')}")
                        if tweet_info.get('images'):
                            print(f"Images: {', '.join(tweet_info.get('images'))}")
                        print("--------------------")

            except Exception as e:
                # print(f"Error during tweet data extraction for an article element: {e}") # Optional: uncomment for debugging extraction issues
                pass # Continue to the next element

        # Update the global set of seen tweet IDs with the ones found in this scroll window
        seen_tweet_ids.update(current_tweet_ids)

        # Check if we actually collected any new tweets in this scroll
        # newly_collected_in_scroll is incremented when we save a tweet (line 892)
        if newly_collected_in_scroll == 0:
             scroll_attempts_without_new_tweets += 1
             print(f"No new unique tweets collected in this scroll. Attempts without new tweets: {scroll_attempts_without_new_tweets}")
             # Stop immediately if we've tried multiple times without finding new tweets
             if scroll_attempts_without_new_tweets >= MAX_SCROLL_ATTEMPTS_WITHOUT_NEW_TWEETS:
                 print(f"Stopping: No new tweets found after {MAX_SCROLL_ATTEMPTS_WITHOUT_NEW_TWEETS} scrolls.")
                 break
        else:
             scroll_attempts_without_new_tweets = 0 # Reset counter if new tweets are found
             print(f"Collected {newly_collected_in_scroll} new unique tweets in this scroll. Total collected: {len(seen_tweet_ids)}")
        
        # Check if we should stop due to date range
        if tweets_outside_date_range >= MAX_TWEETS_OUTSIDE_RANGE:
            print(f"Stopping: Found {tweets_outside_date_range} consecutive tweets outside date range.")
            break


        if limit is not None and collected_count >= limit:
             break

        # Check URL before scrolling to ensure we're still on search page
        current_url_before_scroll = page.url
        if '/search' not in current_url_before_scroll:
            print(f"WARNING: Not on search page before scroll: {current_url_before_scroll}")
            print("Navigating back to search results...")
            await page.goto(search_url, timeout=30000, wait_until='domcontentloaded')
            await asyncio.sleep(1.0)
            continue
        
        # Scroll down
        # print("Scrolling down...") # Optional debug print
        await page.evaluate("window.scrollBy(0, window.innerHeight)")
        await asyncio.sleep(random.uniform(1,2)) # Reduced wait after scroll
        
        # Check URL after scrolling to catch any navigation
        current_url_after_scroll = page.url
        if '/search' not in current_url_after_scroll:
            print(f"WARNING: Navigated away from search page after scroll to: {current_url_after_scroll}")
            print("Navigating back to search results...")
            await page.goto(search_url, timeout=30000, wait_until='domcontentloaded')
            await asyncio.sleep(1.0)
            continue

        new_height = await page.evaluate("document.body.scrollHeight")
        if new_height == last_height:
             print("Reached end of search results or no new tweets loaded after scrolling.")
             scroll_attempts_without_new_tweets += 1 # Increment even if height didn't change
             if scroll_attempts_without_new_tweets >= MAX_SCROLL_ATTEMPTS_WITHOUT_NEW_TWEETS:
                  print(f"Stopping after {MAX_SCROLL_ATTEMPTS_WITHOUT_NEW_TWEETS} scrolls without new content.")
                  break
        else:
             last_height = new_height # Update last_height for the next loop iteration
             # Only reset counter if we actually found NEW tweets, not just because height increased
             # (Height can increase due to ads, suggestions, etc. without new tweets)
             # The counter is already managed above based on newly_collected_in_scroll

    total_collected = len(seen_tweet_ids)
    print(f"Finished scraping loop. Total unique tweets collected: {total_collected}")
    if limit and total_collected < limit:
        print(f"Note: Requested {limit} tweets but only {total_collected} were available.")
    
    # Final save to ensure Excel files are properly written
    if output_file and is_excel_file(output_file) and all_collected_tweets:
        print(f"Saving final results to Excel file: {output_file}")
        save_tweets_to_excel(all_collected_tweets, output_file)
    
    return list(all_collected_tweets) # Ensure we return the list of collected tweets


    async def main_test():
        print("Running standalone search scraper test...")
        test_username = "YOUR_TWITTER_USERNAME" # Replace
        test_password = "YOUR_TWITTER_PASSWORD" # Replace
        test_email = "YOUR_TWITTER_EMAIL" # Optional, replace if needed
        test_keyword = "test" # Replace with your test keyword
        test_since_date = "2023-01-01" # Optional
        test_until_date = "2023-12-31" # Optional
        test_limit = 10 # Optional

        if test_username == "YOUR_TWITTER_USERNAME" or test_password == "YOUR_TWITTER_PASSWORD":
             print("Please replace 'YOUR_TWITTER_USERNAME' and 'YOUR_TWITTER_PASSWORD' with test credentials in __main__ block.")
        else:
            collected_tweets = await scrape_search_results(
                keyword=test_keyword,
                from_account=None,
                username=test_username,
                password=test_password,
                email=test_email,
                since_date=test_since_date,
                until_date=test_until_date,
                limit=test_limit,
                latest=False,
                app_instance=None # Ensure app_instance is None for standalone
                )
            print(f"Standalone test finished. Collected {len(collected_tweets)} tweets.")
            # The tweets would have been printed as they were collected by the new print logic
            # print(json.dumps(collected_tweets, indent=4)) # Uncomment to see JSON output

    # To run the standalone test, uncomment the following line:
    # asyncio.run(main_test())
    print("To run standalone test, uncomment the asyncio.run(main_test()) line in __main__ and replace placeholders.") 