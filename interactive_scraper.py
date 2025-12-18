#!/usr/bin/env python3
"""
Interactive X.com (Twitter) Scraper with Rich Terminal UI
Provides an interactive menu to configure and run tweet scraping.
"""

import json
import sys
import asyncio
import shlex
from datetime import datetime, timedelta
from twitter_search_scraper import scrape_search_results

try:
    from rich.console import Console
    from rich.prompt import Prompt, Confirm
    from rich.panel import Panel
    from rich.text import Text
    from rich.table import Table
except ImportError:
    print("Error: 'rich' library is required. Install it with: pip install rich")
    sys.exit(1)

console = Console()

def format_date(date_str):
    """Format date string to YYYY-MM-DD if needed."""
    try:
        # Try parsing various formats
        for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%m/%d/%Y', '%d/%m/%Y']:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
        # If no format matches, return as is (might be invalid)
        return date_str
    except:
        return date_str

def get_search_type():
    """Ask user for search type."""
    console.print("\n[bold cyan]Select Search Type:[/bold cyan]")
    console.print("1. Keyword search (single or multiple)")
    console.print("2. Account-based search")
    
    choice = Prompt.ask("Enter choice", choices=["1", "2"], default="1")
    return choice

def get_keyword_mode():
    """Ask if user wants single or multiple keywords."""
    console.print("\n[bold cyan]Keyword Mode:[/bold cyan]")
    console.print("1. Single keyword")
    console.print("2. Multiple keywords (OR logic)")
    
    choice = Prompt.ask("Enter choice", choices=["1", "2"], default="1")
    return choice

def get_keywords():
    """Get keywords from user."""
    mode = get_keyword_mode()
    
    def extract_exclusions(keyword_str):
        """Extract account exclusions from keyword(s)."""
        exclusions = []
        kw_clean = keyword_str.strip().lstrip('@').strip()
        if kw_clean:
            exclusions.append(kw_clean.lower())
            if kw_clean.lower() != kw_clean:
                exclusions.append(kw_clean)
        return exclusions
    
    if mode == "1":
        keyword = Prompt.ask("\n[bold]Enter keyword or hashtag[/bold]")
        # Extract account exclusions for single keyword
        exclusions = extract_exclusions(keyword)
        if exclusions:
            # Remove duplicates
            seen = set()
            unique_exclusions = []
            for exc in exclusions:
                if exc.lower() not in seen:
                    seen.add(exc.lower())
                    unique_exclusions.append(exc)
            
            exclusion_str = " ".join(f"-@{acc}" for acc in unique_exclusions)
            full_query = f"{keyword} {exclusion_str}"
            console.print(f"\n[green]Query will be: {full_query}[/green]")
            console.print(f"[dim]Note: Automatically excluding accounts: {', '.join(unique_exclusions)}[/dim]")
        else:
            console.print(f"\n[green]Query will be: {keyword}[/green]")
        return keyword
    else:
        console.print("\n[bold]Enter multiple keywords (press Enter after each, empty to finish):[/bold]")
        keywords = []
        while True:
            kw = Prompt.ask(f"Keyword {len(keywords) + 1}", default="")
            if not kw:
                break
            keywords.append(kw)
        
        if not keywords:
            console.print("[red]Error: At least one keyword is required![/red]")
            return get_keywords()
        
        # Build OR query: (keyword1 OR keyword2 OR keyword3)
        or_query = " OR ".join(f"({kw})" for kw in keywords)
        
        # Extract account exclusions (lowercase and original case variants)
        exclusions = []
        for kw in keywords:
            kw_exclusions = extract_exclusions(kw)
            exclusions.extend(kw_exclusions)
        
        # Remove duplicates
        seen = set()
        unique_exclusions = []
        for exc in exclusions:
            if exc.lower() not in seen:
                seen.add(exc.lower())
                unique_exclusions.append(exc)
        
        if unique_exclusions:
            exclusion_str = " ".join(f"-@{acc}" for acc in unique_exclusions)
            full_query = f"{or_query} {exclusion_str}"
            console.print(f"\n[green]Query will be: {full_query}[/green]")
            console.print(f"[dim]Note: Automatically excluding accounts: {', '.join(unique_exclusions)}[/dim]")
        else:
            console.print(f"\n[green]Query will be: {or_query}[/green]")
        
        return or_query

def get_account():
    """Get account name from user."""
    account = Prompt.ask("\n[bold]Enter account username[/bold] (without @)")
    return account.lstrip('@')

def get_date_range():
    """Ask user for date range."""
    use_dates = Confirm.ask("\n[bold]Do you want to filter by date range?[/bold]", default=False)
    
    if not use_dates:
        return None, None
    
    console.print("\n[bold cyan]Date Range:[/bold cyan]")
    console.print("Enter dates in YYYY-MM-DD format (or press Enter for today/yesterday)")
    
    since_date = Prompt.ask("Start date (since)", default="")
    until_date = Prompt.ask("End date (until)", default="")
    
    # Default to today if not provided
    if not until_date:
        until_date = datetime.now().strftime('%Y-%m-%d')
    
    # Default to yesterday if not provided
    if not since_date:
        since_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    since_date = format_date(since_date)
    until_date = format_date(until_date)
    
    return since_date, until_date

def get_latest_mode():
    """Ask if user wants latest mode."""
    use_latest = Confirm.ask("\n[bold]Use latest mode?[/bold] (searches in Latest tab with f=live)", default=True)
    return use_latest

def get_limit():
    """Get tweet limit from user."""
    limit_str = Prompt.ask("\n[bold]Maximum number of tweets to collect[/bold]", default="100")
    try:
        return int(limit_str)
    except ValueError:
        console.print("[red]Invalid number, using default: 100[/red]")
        return 100

def get_output_format():
    """Ask user for output format."""
    console.print("\n[bold cyan]Output Format:[/bold cyan]")
    console.print("1. JSON (.json)")
    console.print("2. Excel (.xlsx)")
    
    choice = Prompt.ask("Enter choice", choices=["1", "2"], default="1")
    return choice

def get_output_file():
    """Get output filename from user."""
    format_choice = get_output_format()
    
    if format_choice == "2":
        default_file = f"scraped_tweets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        output = Prompt.ask("\n[bold]Output filename[/bold]", default=default_file)
        if not output.endswith('.xlsx') and not output.endswith('.xls'):
            output += '.xlsx'
    else:
        default_file = f"scraped_tweets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        output = Prompt.ask("\n[bold]Output filename[/bold]", default=default_file)
        if not output.endswith('.json'):
            output += '.json'
    
    return output

def generate_command(search_type, keyword, account, since_date, until_date, latest, limit, output):
    """Generate the command string that can be run directly."""
    cmd_parts = ["python", "run_search_scraper.py"]
    
    if search_type == "1":
        # Keyword search
        cmd_parts.append(f'--keyword')
        # Properly escape the keyword for shell
        cmd_parts.append(shlex.quote(keyword))
    else:
        # Account search
        cmd_parts.append(f'--from-account')
        cmd_parts.append(shlex.quote(account))
    
    # Add limit
    cmd_parts.append(f'--limit')
    cmd_parts.append(str(limit))
    
    # Add latest flag if enabled
    if latest:
        cmd_parts.append('--latest')
    
    # Add date filters if provided
    if since_date:
        cmd_parts.append(f'--since-date')
        cmd_parts.append(shlex.quote(since_date))
    
    if until_date:
        cmd_parts.append(f'--until-date')
        cmd_parts.append(shlex.quote(until_date))
    
    # Add output file
    cmd_parts.append(f'--output')
    cmd_parts.append(shlex.quote(output))
    
    return " ".join(cmd_parts)

def display_summary(search_type, keyword, account, since_date, until_date, latest, limit, output):
    """Display a summary of the scraping configuration."""
    table = Table(title="Scraping Configuration", show_header=True, header_style="bold magenta")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    
    if search_type == "1":
        table.add_row("Search Type", "Keyword")
        table.add_row("Keyword(s)", keyword)
    else:
        table.add_row("Search Type", "Account")
        table.add_row("Account", f"@{account}")
    
    if since_date and until_date:
        table.add_row("Date Range", f"{since_date} to {until_date}")
    else:
        table.add_row("Date Range", "Not specified")
    
    table.add_row("Latest Mode", "Yes" if latest else "No")
    table.add_row("Limit", str(limit))
    output_format = "Excel (.xlsx)" if output.endswith('.xlsx') or output.endswith('.xls') else "JSON (.json)"
    table.add_row("Output Format", output_format)
    table.add_row("Output File", output)
    
    console.print("\n")
    console.print(table)
    console.print()
    
    # Note: Command will be displayed separately in main() for better visibility

def run_scraper(keyword, account, since_date, until_date, latest, limit, output):
    """Run the scraper with the given parameters."""
    console.print("\n[bold yellow]Starting scraper...[/bold yellow]\n")
    
    try:
        collected_tweets = asyncio.run(scrape_search_results(
            keyword=keyword,
            from_account=account,
            username=None,
            password=None,
            email=None,
            since_date=since_date,
            until_date=until_date,
            limit=limit,
            latest=latest,
            output_file=output
        ))
        
        console.print(f"\n[bold green]✓ Scraping finished![/bold green]")
        console.print(f"[green]Collected {len(collected_tweets)} tweets saved to {output}[/green]")
        return True
        
    except Exception as e:
        console.print(f"\n[bold red]✗ Error occurred:[/bold red] {e}")
        return False

def main():
    """Main interactive function."""
    console.print(Panel.fit(
        "[bold cyan]X.com (Twitter) Interactive Scraper[/bold cyan]\n"
        "Configure your search and scrape tweets interactively",
        border_style="cyan"
    ))
    
    # Get search type
    search_type = get_search_type()
    
    keyword = None
    account = None
    
    if search_type == "1":
        keyword = get_keywords()
    else:
        account = get_account()
    
    # Get date range
    since_date, until_date = get_date_range()
    
    # Get latest mode
    latest = get_latest_mode()
    
    # Get limit
    limit = get_limit()
    
    # Get output file
    output = get_output_file()
    
    # Generate command first
    command = generate_command(search_type, keyword, account, since_date, until_date, latest, limit, output)
    
    # Display summary
    display_summary(search_type, keyword, account, since_date, until_date, latest, limit, output)
    
    # Display command prominently before running
    console.print("\n")
    console.print(Panel(
        f"[bold bright_yellow]{command}[/bold bright_yellow]",
        title="[bold bright_cyan]📋 Command to run directly (copy this):[/bold bright_cyan]",
        border_style="bright_yellow",
        padding=(1, 2)
    ))
    console.print()
    
    # Confirm before running
    if not Confirm.ask("[bold]Start scraping?[/bold]", default=True):
        console.print("[yellow]Cancelled by user.[/yellow]")
        console.print(f"\n[bold]You can run the command manually:[/bold]")
        console.print(f"[bright_yellow]{command}[/bright_yellow]")
        return
    
    # Run scraper
    success = run_scraper(keyword, account, since_date, until_date, latest, limit, output)
    
    if success:
        console.print("\n[bold green]✓ Done![/bold green]")
    else:
        console.print("\n[bold red]✗ Scraping failed. Check the error messages above.[/bold red]")
    
    # Display command again prominently after scraping for easy copying
    console.print("\n")
    console.print(Panel(
        f"[bold bright_yellow]{command}[/bold bright_yellow]",
        title="[bold bright_cyan]📋 Command used (copy for future use):[/bold bright_cyan]",
        border_style="bright_yellow",
        padding=(1, 2)
    ))
    console.print(f"[dim]Tip: You can copy and paste this command to run the scraper again with the same settings.[/dim]")
    console.print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user.[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[bold red]Unexpected error:[/bold red] {e}")
        sys.exit(1)
