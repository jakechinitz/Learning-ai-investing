"""
Twitter/X Content Fetcher
Fetches recent posts from tracked accounts

NOTE: Twitter API has strict rate limits and costs.
This module provides multiple approaches:
1. Manual curation (recommended for quality)
2. Nitter RSS feeds (free, but unreliable)
3. Official API (requires paid access)
"""

import feedparser
from datetime import datetime, timedelta
from typing import Optional
import yaml
from pathlib import Path
import json


def load_sources() -> dict:
    """Load sources from config file."""
    config_path = Path(__file__).parent.parent.parent / "config" / "sources.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


def get_nitter_rss_url(handle: str, nitter_instance: str = "nitter.net") -> str:
    """
    Generate Nitter RSS URL for a Twitter handle.
    Note: Nitter instances come and go - may need to update.
    """
    clean_handle = handle.replace("@", "")
    return f"https://{nitter_instance}/{clean_handle}/rss"


def fetch_twitter_via_nitter(
    handle: str,
    days_back: int = 1,
    nitter_instance: str = "nitter.privacydev.net"
) -> list[dict]:
    """
    Fetch tweets via Nitter RSS feed.

    Note: Nitter is often blocked or rate-limited.
    This is a best-effort approach.
    """
    posts = []
    cutoff = datetime.now() - timedelta(days=days_back)
    rss_url = get_nitter_rss_url(handle, nitter_instance)

    try:
        feed = feedparser.parse(rss_url)

        for entry in feed.entries:
            published = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                published = datetime(*entry.published_parsed[:6])

            if published and published < cutoff:
                continue

            post = {
                'handle': handle,
                'content': entry.get('title', '')[:500],
                'link': entry.get('link', ''),
                'published': published.isoformat() if published else None,
                'source_type': 'twitter',
            }
            posts.append(post)

    except Exception as e:
        print(f"Error fetching @{handle} via Nitter: {e}")

    return posts


def create_manual_twitter_digest(highlights: list[dict]) -> list[dict]:
    """
    Create a digest from manually curated Twitter highlights.

    This is the recommended approach for quality:
    - Save interesting tweets you find during the day
    - Add to highlights.json
    - Include in daily digest

    Args:
        highlights: List of dicts with handle, content, reasoning, link

    Returns:
        Formatted list of posts
    """
    return [{
        'handle': h.get('handle', 'Unknown'),
        'content': h.get('content', ''),
        'reasoning': h.get('reasoning', ''),  # Why this tweet matters
        'link': h.get('link', ''),
        'stocks_mentioned': h.get('stocks_mentioned', []),
        'source_type': 'twitter_curated',
        'published': h.get('date', datetime.now().isoformat()),
    } for h in highlights]


def fetch_all_twitter(days_back: int = 1, use_nitter: bool = False) -> list[dict]:
    """
    Fetch Twitter content from all configured accounts.

    Args:
        days_back: How many days back to fetch
        use_nitter: Whether to attempt Nitter fetch (often fails)

    Returns:
        List of posts
    """
    sources = load_sources()
    all_posts = []

    if use_nitter:
        for account in sources.get('twitter', []):
            handle = account.get('handle', '').replace('@', '')
            if not handle:
                continue

            posts = fetch_twitter_via_nitter(handle, days_back)

            for post in posts:
                post['focus'] = account.get('focus', '')
                post['why_follow'] = account.get('why_follow', '')

            all_posts.extend(posts)

    # Also check for curated highlights
    highlights_path = Path(__file__).parent.parent.parent / "data" / "twitter_highlights.json"
    if highlights_path.exists():
        try:
            with open(highlights_path) as f:
                highlights = json.load(f)
            curated = create_manual_twitter_digest(highlights.get('recent', []))
            all_posts.extend(curated)
        except Exception as e:
            print(f"Error loading Twitter highlights: {e}")

    return all_posts


def get_twitter_accounts_to_follow() -> list[dict]:
    """Return list of Twitter accounts to follow with context."""
    sources = load_sources()
    return sources.get('twitter', [])


if __name__ == "__main__":
    print("Twitter Accounts to Follow for AI Investing:\n")
    accounts = get_twitter_accounts_to_follow()

    for acc in accounts:
        print(f"{acc['handle']}")
        print(f"  Focus: {acc.get('focus', 'N/A')}")
        print(f"  Why: {acc.get('why_follow', 'N/A')}")
        print()
