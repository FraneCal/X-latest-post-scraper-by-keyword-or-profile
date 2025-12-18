import json
import sys
import asyncio
import argparse
from datetime import datetime
from twitter_search_scraper import scrape_search_results

def run_search_from_args(args):
    """Runs the Twitter search scraper using command-line arguments."""
    keyword = args.keyword
    from_account = args.from_account
    limit = args.limit
    since_date = args.since_date
    until_date = args.until_date
    output_file = args.output or 'scraped_search_tweets.json'
    username = args.username
    password = args.password
    email = args.email

    if from_account:
        print(f"Starting search scraper for account: @{from_account}")
    elif keyword:
        print(f"Starting search scraper for keyword: {keyword}")
    else:
        print("Error: Either --keyword or --from-account must be provided")
        sys.exit(1)
    
    if args.latest:
        print("Mode: Latest tweets (last 24 hours)")
    elif since_date or until_date:
        print(f"Date range: {since_date or 'None'} to {until_date or 'None'}")
    print(f"Limit: {limit}")
    print(f"Output file: {output_file}")
    print()

    # Run the asynchronous scraper (tweets are saved incrementally during scraping)
    collected_tweets = asyncio.run(scrape_search_results(
        keyword=keyword,
        from_account=from_account,  # New parameter for account-based search
        username=username,  # Optional if browser profile exists
        password=password,  # Optional if browser profile exists
        email=email,
        since_date=since_date,
        until_date=until_date,
        limit=limit,
        latest=args.latest,
        output_file=output_file  # Pass output file for incremental saving
    ))

    print(f"\nScraping finished. Collected {len(collected_tweets)} tweets saved to {output_file}")

def run_search_from_config(config_file):
    """Reads configuration from a JSON file and runs the Twitter search scraper."""
    try:
        # Explicitly open with utf-8 encoding
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)

        username = config.get('username')
        password = config.get('password')
        email = config.get('email')
        # Read keywords as a list
        keywords = config.get('keywords')
        # Read the flag for OR logic
        use_or_logic = config.get('use_or_logic', False) # Default to False

        since_date_str = config.get('since_date')
        until_date_str = config.get('until_date')
        limit = config.get('limit')
        output_file = config.get('output_file', 'scraped_search_tweets.json') # Default output file

        # Construct the search keyword string based on logic
        if use_or_logic and isinstance(keywords, list) and keywords:
            search_keyword_string = " OR ".join(f'({kw})' for kw in keywords)
            print(f"Using OR logic for keywords: {keywords}")
        elif isinstance(keywords, list) and keywords:
             # If not using OR logic, just join with spaces (standard search)
             search_keyword_string = " ".join(keywords)
             print(f"Using AND logic for keywords: {keywords}")
        elif isinstance(keywords, str) and keywords:
             # Handle case where keywords is a single string for backward compatibility
             search_keyword_string = keywords
             print(f"Using single keyword: {keywords}")
        else:
             print("Error: 'keywords' in config file is invalid.")
             sys.exit(1)

        print(f"Starting search scraper for keyword query: {search_keyword_string}")
        print(f"Date range: {since_date_str} to {until_date_str}")
        print(f"Limit: {limit}")

        # Run the asynchronous scraper, passing the constructed search_keyword_string
        # Tweets are saved incrementally during scraping
        collected_tweets = asyncio.run(scrape_search_results(
            keyword=search_keyword_string, # Pass the constructed string
            from_account=None,  # Config file mode doesn't support from_account
            username=username,  # Optional if browser profile exists
            password=password,  # Optional if browser profile exists
            email=email,
            since_date=since_date_str,
            until_date=until_date_str,
            limit=limit,
            latest=False,  # Config file mode doesn't support latest flag
            output_file=output_file  # Pass output file for incremental saving
        ))

        # The scrape_search_results function returns the list of collected tweets directly
        filtered_tweets = collected_tweets # Assuming filtering is done within the scraper based on date strings

        print(f"Scraping finished. Collected {len(filtered_tweets)} tweets saved to {output_file}")

    except FileNotFoundError:
        print(f"Error: Config file not found at {config_file}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Could not parse JSON from {config_file}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description='Scrape tweets from X.com (Twitter) based on search keywords',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search by keyword/hashtag
  python run_search_scraper.py --keyword "#elonmusk" --limit 100
  python run_search_scraper.py --keyword "#elonmusk" --limit 100 --latest  # Latest tweets from last 24 hours
  python run_search_scraper.py --keyword "python programming" --limit 50 --since-date "2025-01-01"
  
  # Search tweets from a specific account
  python run_search_scraper.py --from-account "elonmusk" --limit 100 --latest
  python run_search_scraper.py --from-account "elonmusk" --limit 200 --output "elonmusk_tweets.json"
  
  python run_search_scraper.py config_search.json  # Use config file (legacy mode)
        """
    )
    
    # Main arguments
    parser.add_argument('--keyword', '-k', type=str, help='Search keyword or hashtag (e.g., "#elonmusk")')
    parser.add_argument('--from-account', '-a', type=str, help='Get tweets from a specific account (e.g., "elonmusk" for @elonmusk)')
    parser.add_argument('--limit', '-l', type=int, help='Maximum number of tweets to collect')
    parser.add_argument('--since-date', '-s', type=str, help='Start date in YYYY-MM-DD format')
    parser.add_argument('--until-date', '-u', type=str, help='End date in YYYY-MM-DD format')
    parser.add_argument('--output', '-o', type=str, help='Output JSON file name (default: scraped_search_tweets.json)')
    parser.add_argument('--latest', action='store_true', help='Get latest tweets from last 24 hours (uses f=live parameter)')
    
    # Optional credentials (only needed if browser profile doesn't work)
    parser.add_argument('--username', type=str, help='X.com username (optional if browser profile exists)')
    parser.add_argument('--password', type=str, help='X.com password (optional if browser profile exists)')
    parser.add_argument('--email', type=str, help='X.com email (optional, for verification)')
    
    # Support config file as positional argument (backward compatibility)
    parser.add_argument('config_file', nargs='?', help='Config file path (optional, use --keyword instead)')
    
    args = parser.parse_args()
    
    # Check if config file is provided (legacy mode)
    if args.config_file and not args.keyword and not args.from_account:
        # Legacy mode: use config file
        run_search_from_config(args.config_file)
    elif args.keyword or args.from_account:
        # New mode: use command-line arguments
        run_search_from_args(args)
    else:
        # No arguments provided
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
