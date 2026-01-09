"""
Podcast Feed Fetcher
Fetches recent episodes from AI/tech investing podcasts
"""

import feedparser
from datetime import datetime, timedelta
from typing import Optional
import yaml
from pathlib import Path
import re


def load_sources() -> dict:
    """Load sources from config file."""
    config_path = Path(__file__).parent.parent.parent / "config" / "sources.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


def extract_stocks_from_title(title: str, watchlist: dict) -> list[str]:
    """
    Extract stock mentions from episode title.

    Args:
        title: Episode title
        watchlist: Dict of stock categories with symbols

    Returns:
        List of stock symbols mentioned
    """
    mentioned = []
    title_upper = title.upper()

    # Flatten watchlist
    all_stocks = []
    for category in watchlist.values():
        if isinstance(category, list):
            all_stocks.extend(category)

    for stock in all_stocks:
        symbol = stock.get('symbol', '')
        name = stock.get('name', '')

        # Check for symbol mention
        if symbol and re.search(rf'\b{symbol}\b', title_upper):
            mentioned.append(symbol)
        # Check for company name mention
        elif name and name.lower() in title.lower():
            mentioned.append(symbol)

    return list(set(mentioned))


def fetch_podcast_feed(
    feed_url: str,
    days_back: int = 7
) -> list[dict]:
    """
    Fetch recent episodes from a podcast RSS feed.

    Args:
        feed_url: The podcast RSS feed URL
        days_back: How many days back to fetch (default 7 for weekly)

    Returns:
        List of episode dicts
    """
    episodes = []
    cutoff = datetime.now() - timedelta(days=days_back)

    try:
        feed = feedparser.parse(feed_url)

        for entry in feed.entries:
            published = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                published = datetime(*entry.published_parsed[:6])

            if published and published < cutoff:
                continue

            # Get duration if available
            duration = None
            if hasattr(entry, 'itunes_duration'):
                duration = entry.itunes_duration

            episode = {
                'title': entry.get('title', 'No title'),
                'link': entry.get('link', ''),
                'summary': entry.get('summary', '')[:500],
                'published': published.isoformat() if published else None,
                'duration': duration,
                'source_type': 'podcast',
            }
            episodes.append(episode)

    except Exception as e:
        print(f"Error fetching {feed_url}: {e}")

    return episodes


def fetch_all_podcasts(days_back: int = 7) -> list[dict]:
    """
    Fetch episodes from all configured podcasts.

    Args:
        days_back: How many days back to fetch

    Returns:
        List of all episodes with source metadata
    """
    sources = load_sources()
    all_episodes = []
    watchlist = sources.get('watchlist', {})

    for podcast in sources.get('podcasts', []):
        feed_url = podcast.get('feed')
        if not feed_url:
            continue

        episodes = fetch_podcast_feed(feed_url, days_back)

        for episode in episodes:
            episode['podcast_name'] = podcast.get('name', 'Unknown')
            episode['focus'] = podcast.get('focus', '')
            episode['why_listen'] = podcast.get('why_listen', '')
            episode['hosts'] = podcast.get('hosts', podcast.get('host', ''))

            # Extract stock mentions from title
            episode['stocks_mentioned'] = extract_stocks_from_title(
                episode['title'],
                watchlist
            )

        all_episodes.extend(episodes)

    # Sort by date, most recent first
    all_episodes.sort(key=lambda x: x.get('published', ''), reverse=True)

    return all_episodes


def get_podcast_list() -> list[dict]:
    """Return list of podcasts to follow with context."""
    sources = load_sources()
    return sources.get('podcasts', [])


if __name__ == "__main__":
    print("Fetching podcast episodes from last 7 days...\n")
    episodes = fetch_all_podcasts(days_back=7)

    for ep in episodes[:10]:  # Show first 10
        stocks = ep.get('stocks_mentioned', [])
        stock_str = f" [{', '.join(stocks)}]" if stocks else ""
        print(f"{ep['podcast_name']}: {ep['title']}{stock_str}")
        print(f"  Published: {ep['published']}")
        print(f"  Duration: {ep.get('duration', 'N/A')}")
        print()
