import json
import sys
import asyncio
import argparse
from datetime import date, timedelta
from twitter_search_scraper import scrape_search_results


def get_month_date_range():
    today = date.today()
    since_date = today.replace(day=1).isoformat()
    until_date = (today + timedelta(days=1)).isoformat()
    return since_date, until_date


def load_lines_from_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def tag_and_reorder_tweets(tweets, search_value):
    tagged = []
    for tweet in tweets:
        new_tweet = {"search_value": search_value}
        new_tweet.update(tweet)
        tagged.append(new_tweet)
    return tagged


def run_search_from_args(args):
    limit = args.limit
    output_file = args.output or "scraped_search_tweets.xlsx"
    username = args.username
    password = args.password
    email = args.email

    since_date, until_date = get_month_date_range()

    keyword_queries = []
    profiles = []

    if args.keywords_file:
        keyword_queries = load_lines_from_file(args.keywords_file)

    if args.profiles_file:
        profiles = load_lines_from_file(args.profiles_file)

    if args.keyword:
        keyword_queries = [args.keyword]

    if args.from_account:
        profiles = [args.from_account]

    if not keyword_queries and not profiles:
        print("Error: No keywords or profiles provided")
        sys.exit(1)

    all_collected = []

    for kw in keyword_queries:
        print(f"Keyword search: {kw}")
        print(f"Date range: {since_date} to {until_date}")
        print(f"Limit: {limit}")
        print()

        collected = asyncio.run(
            scrape_search_results(
                keyword=kw,
                from_account=None,
                username=username,
                password=password,
                email=email,
                since_date=since_date,
                until_date=until_date,
                limit=limit,
                latest=args.latest,
                output_file=output_file,
            )
        )

        collected = tag_and_reorder_tweets(collected, kw)
        all_collected.extend(collected)

    for profile in profiles:
        print(f"Profile search: @{profile}")
        print(f"Date range: {since_date} to {until_date}")
        print(f"Limit: {limit}")
        print()

        collected = asyncio.run(
            scrape_search_results(
                keyword=None,
                from_account=profile,
                username=username,
                password=password,
                email=email,
                since_date=since_date,
                until_date=until_date,
                limit=limit,
                latest=args.latest,
                output_file=output_file,
            )
        )

        collected = tag_and_reorder_tweets(collected, profile)
        all_collected.extend(collected)

    print(
        f"\nScraping finished. Collected {len(all_collected)} tweets saved to {output_file}"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Scrape tweets from X.com using keywords or profiles"
    )

    parser.add_argument("--keyword", "-k", type=str)
    parser.add_argument("--keywords-file", type=str)
    parser.add_argument("--from-account", "-a", type=str)
    parser.add_argument("--profiles-file", type=str)

    parser.add_argument("--limit", "-l", type=int)
    parser.add_argument("--output", "-o", type=str)
    parser.add_argument("--latest", action="store_true")

    parser.add_argument("--username", type=str)
    parser.add_argument("--password", type=str)
    parser.add_argument("--email", type=str)

    args = parser.parse_args()
    run_search_from_args(args)


if __name__ == "__main__":
    main()