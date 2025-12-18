# Twitter Search Scraper CLI

This application is a Command-Line Interface (CLI) tool designed to scrape tweets from X.com (Twitter) based on search keywords or specific accounts.

## Prerequisites

Before running the application, ensure you have completed the necessary setup steps:

1. **Python Installation:** Have Python 3.7+ installed.
2. **Navigate to Project Directory:** Open your terminal or command prompt and navigate to the project directory.

   ```bash
   cd d:\vscode\Frane\XScraper
   ```

3. **Virtual Environment Activation (Optional):** If you are using a virtual environment for this project, activate it.

   * On Linux/Mac:
     ```bash
     source .venv/bin/activate
     ```
   * On Windows:
     ```bash
     .\.venv\Scripts\activate
     ```

4. **Dependency Installation:** Install the required libraries.

   ```bash
   pip install -r requirements.txt
   ```

   Install Playwright browsers:

   ```bash
   playwright install
   ```

## ⚠️ IMPORTANT: Initial Setup - Login and Save Browser Profile

**YOU MUST RUN THIS STEP FIRST BEFORE USING THE SCRAPER!**

The scraper uses a persistent browser profile to maintain your login session. You need to login once and save your browser profile before you can use the scraper.

### Step 1: Run the Login Script

```bash
python login_and_save_profile.py
```

### Step 2: Manual Login Process

1. **Press ENTER** when prompted to start
2. A browser window will open automatically
3. **Log in to X.com manually** in the opened browser:
   - Enter your username/email and password
   - Complete any CAPTCHA or verification steps
   - Handle 2FA if enabled
   - Wait until you're fully logged in and see your X.com home feed

### Step 3: Save the Profile

1. Once you're logged in successfully, **go back to the terminal**
2. **Press ENTER** in the terminal
3. The script will verify your login and save the browser profile
4. You'll see a confirmation message when the profile is saved

### Step 4: Profile Location

Your browser profile (with saved login session) will be stored in the `browser_profile/` directory. The scraper will automatically use this profile for all future runs.

**Note:** 
- You only need to do this **once** (unless your session expires)
- If X.com asks you to login again later, simply re-run `login_and_save_profile.py` to refresh your session
- The browser profile contains your cookies and session data, so keep it secure

## Running the Scraper

**⚠️ Make sure you've completed the login setup above first!**

Once you've saved your browser profile, you can run the scraper in two ways:

### Method 1: Using Command-Line Arguments (Recommended)

#### Search by Keyword/Hashtag:

```bash
# Search for latest tweets with a hashtag
python run_search_scraper.py --keyword "#elonmusk" --limit 100 --latest

# Search with date range
python run_search_scraper.py --keyword "python programming" --limit 50 --since-date "2025-01-01" --until-date "2025-01-31"

# Search and save to custom file
python run_search_scraper.py --keyword "#elonmusk" --limit 100 --output "my_tweets.json"
```

#### Search Tweets from a Specific Account:

```bash
# Get latest tweets from an account
python run_search_scraper.py --from-account "elonmusk" --limit 100 --latest

# Get tweets with date range
python run_search_scraper.py --from-account "elonmusk" --limit 200 --since-date "2025-01-01" --until-date "2025-01-31"
```

#### Available Arguments:

- `--keyword` or `-k`: Search keyword or hashtag (e.g., "#elonmusk")
- `--from-account` or `-a`: Get tweets from a specific account (e.g., "elonmusk" for @elonmusk)
- `--limit` or `-l`: Maximum number of tweets to collect
- `--since-date` or `-s`: Start date in YYYY-MM-DD format
- `--until-date` or `-u`: End date in YYYY-MM-DD format
- `--output` or `-o`: Output JSON file name (default: scraped_search_tweets.json)
- `--latest`: Get latest tweets from last 24 hours (uses f=live parameter)

### Method 2: Using Configuration File (Legacy Mode)

You can also use a JSON configuration file:

1. **Create a Configuration File:** Create or modify `config_search.json`:

   ```json
   {
       "username": "YOUR_TWITTER_USERNAME",
       "password": "YOUR_TWITTER_PASSWORD",
       "email": "YOUR_TWITTER_EMAIL",
       "keywords": ["keyword1", "keyword2"],
       "use_or_logic": true,
       "since_date": "2025-01-01",
       "until_date": "2025-05-30",
       "limit": 100,
       "output_file": "scraped_search_tweets.json"
   } 
   ```

   **Note:** If you've already set up the browser profile, the `username` and `password` fields are optional and only used if the session expires.

2. **Run with Config File:**

   ```bash
   python run_search_scraper.py config_search.json
   ```

## Key Files

* **`run_search_scraper.py`:** This is the main Python file that contains the CLI logic. It parses command-line arguments and executes the scraping functions.
* **`login_and_save_profile.py`:** **Run this first!** Script to login to x.com and save a persistent browser profile. You must run this before using the scraper.
* **`twitter_search_scraper.py`:** Contains the core scraping logic that uses the saved browser profile for authentication.
* **`config_search.json`:** A JSON file used to provide input parameters (search terms, dates, output file name, etc.) to the CLI script (legacy mode).
* **`requirements.txt`:** Lists the Python packages required for this CLI scraper to run. You use `pip install -r requirements.txt` to install them.
* **`browser_profile/`:** Directory containing the saved browser profile with login session. This is automatically created when you run `login_and_save_profile.py`. The scraper uses this profile to maintain your login session.

## Output Location

The scraped data will be saved to a JSON file. The output file name can be specified using:
- The `--output` or `-o` argument when using command-line mode
- The `output_file` field in the configuration file when using config file mode

The default output file name is `scraped_search_tweets.json` if not specified.

## Output Data Format

Each tweet in the output JSON file contains the following fields:

- `id`: Tweet ID
- `views`: Number of views
- `replies`: Number of replies
- `reposts`: Number of reposts/retweets
- `likes`: Number of likes
- `body`: Tweet text content
- `url`: Tweet URL
- `date`: Tweet date in ISO format
- `author`: Tweet author username
- `profile_followers`: Number of followers for the tweet author
- `link`: Tweet link (same as url)
- `username`: Author username
- `display_name`: Author display name
- `text`: Tweet text (same as body)
- `images`: Array of image URLs (profile images and media)

## Troubleshooting

### Session Expired / Login Required

If you see an error message asking you to login:

1. Re-run the login script:
   ```bash
   python login_and_save_profile.py
   ```
2. Complete the login process again
3. Try running the scraper again

### Browser Profile Locked

If you see a warning about the browser profile being locked:

1. Close all Chrome/Chromium browser windows
2. Wait a few seconds
3. Try running the scraper again

### No Tweets Found

- Check that your search keywords are correct
- Verify that tweets matching your criteria exist
- Try using `--latest` flag for recent tweets
- Check the date range if using date filters
