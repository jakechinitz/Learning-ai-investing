"""
Substack RSS Feed Fetcher
Fetches recent articles from Substack newsletters
"""

import feedparser
from datetime import datetime, timedelta
from typing import Optional
import yaml
from pathlib import Path


def load_sources() -> dict:
    """Load sources from config file."""
    config_path = Path(__file__).parent.parent.parent / "config" / "sources.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


def fetch_substack_feed(
    rss_url: str,
    days_back: int = 1
) -> list[dict]:
    """
    Fetch recent articles from a Substack RSS feed.

    Args:
        rss_url: The RSS feed URL
        days_back: How many days back to fetch (default 1 for daily)

    Returns:
        List of article dicts with title, summary, link, published date
    """
    articles = []
    cutoff = datetime.now() - timedelta(days=days_back)

    try:
        feed = feedparser.parse(rss_url)

        for entry in feed.entries:
            # Parse published date
            published = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                published = datetime(*entry.published_parsed[:6])
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                published = datetime(*entry.updated_parsed[:6])

            # Skip old articles
            if published and published < cutoff:
                continue

            article = {
                'title': entry.get('title', 'No title'),
                'link': entry.get('link', ''),
                'summary': entry.get('summary', '')[:500],  # Truncate long summaries
                'published': published.isoformat() if published else None,
                'source_type': 'substack',
            }
            articles.append(article)

    except Exception as e:
        print(f"Error fetching {rss_url}: {e}")

    return articles


def fetch_all_substacks(days_back: int = 1) -> list[dict]:
    """
    Fetch articles from all configured Substacks.

    Returns:
        List of all articles with source name added
    """
    sources = load_sources()
    all_articles = []

    for substack in sources.get('substacks', []):
        rss_url = substack.get('rss')
        if not rss_url:
            continue

        articles = fetch_substack_feed(rss_url, days_back)

        # Add source metadata
        for article in articles:
            article['source_name'] = substack.get('name', 'Unknown')
            article['focus'] = substack.get('focus', '')
            article['must_read'] = substack.get('must_read', False)

        all_articles.extend(articles)

    # Sort by must_read first, then by date
    all_articles.sort(
        key=lambda x: (not x.get('must_read', False), x.get('published', '')),
        reverse=True
    )

    return all_articles


if __name__ == "__main__":
    # Test the fetcher
    print("Fetching Substack articles from last 7 days...")
    articles = fetch_all_substacks(days_back=7)

    for article in articles:
        must_read = "🔥 " if article.get('must_read') else ""
        print(f"\n{must_read}{article['source_name']}: {article['title']}")
        print(f"  Link: {article['link']}")
        print(f"  Published: {article['published']}")
