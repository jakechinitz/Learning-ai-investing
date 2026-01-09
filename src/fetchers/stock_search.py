"""
Stock-Centric Social Search
Searches across multiple sources for mentions of specific stock tickers
More like Grok - finds what people are saying about each stock
"""

import feedparser
import requests
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path
from urllib.parse import quote_plus
import yaml
import re
import time

try:
    import yfinance as yf
except ImportError:
    yf = None


def load_watchlist() -> dict:
    """Load all stocks from watchlist configuration."""
    config_path = Path(__file__).parent.parent.parent / "config" / "sources.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)
    return config.get('watchlist', {})


def get_all_tickers() -> list[dict]:
    """Get flat list of all tickers with their info."""
    watchlist = load_watchlist()
    all_stocks = []

    for category, stocks in watchlist.items():
        if not isinstance(stocks, list):
            continue
        for stock in stocks:
            stock['category'] = category
            all_stocks.append(stock)

    return all_stocks


def search_google_news(ticker: str, company_name: str, days_back: int = 1) -> list[dict]:
    """
    Search Google News RSS for ticker/company mentions.
    Returns list of news articles.
    """
    results = []

    # Search both ticker and company name
    queries = [
        f"{ticker} stock",
        f"{company_name} stock",
    ]

    for query in queries:
        try:
            url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
            feed = feedparser.parse(url)

            cutoff = datetime.now() - timedelta(days=days_back)

            for entry in feed.entries[:5]:  # Limit per query
                published = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6])

                if published and published < cutoff:
                    continue

                # Check if ticker or company is actually mentioned
                title = entry.get('title', '').upper()
                if ticker.upper() not in title and company_name.upper() not in title.upper():
                    continue

                result = {
                    'source': 'Google News',
                    'title': entry.get('title', ''),
                    'link': entry.get('link', ''),
                    'published': published.isoformat() if published else None,
                    'summary': entry.get('summary', '')[:300],
                    'ticker': ticker,
                }
                results.append(result)

        except Exception as e:
            print(f"Error searching Google News for {ticker}: {e}")

    # Deduplicate by title
    seen_titles = set()
    unique_results = []
    for r in results:
        title_key = r['title'].lower()[:50]
        if title_key not in seen_titles:
            seen_titles.add(title_key)
            unique_results.append(r)

    return unique_results


def search_substack_for_ticker(ticker: str, days_back: int = 3) -> list[dict]:
    """
    Search Substack RSS feeds for ticker mentions.
    """
    config_path = Path(__file__).parent.parent.parent / "config" / "sources.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)

    substacks = config.get('substacks', [])
    results = []
    cutoff = datetime.now() - timedelta(days=days_back)

    for sub in substacks:
        rss_url = sub.get('rss')
        if not rss_url:
            continue

        try:
            feed = feedparser.parse(rss_url)

            for entry in feed.entries[:10]:
                # Check if ticker is mentioned
                title = entry.get('title', '').upper()
                content = entry.get('summary', '').upper()

                if ticker.upper() not in title and ticker.upper() not in content:
                    continue

                published = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6])

                if published and published < cutoff:
                    continue

                result = {
                    'source': sub.get('name', 'Substack'),
                    'title': entry.get('title', ''),
                    'link': entry.get('link', ''),
                    'published': published.isoformat() if published else None,
                    'summary': entry.get('summary', '')[:500],
                    'ticker': ticker,
                    'must_read': sub.get('must_read', False),
                }
                results.append(result)

        except Exception as e:
            print(f"Error searching {sub.get('name')} for {ticker}: {e}")

    return results


def search_nitter_for_ticker(
    ticker: str,
    days_back: int = 1,
    nitter_instances: list[str] = None
) -> list[dict]:
    """
    Search Nitter (Twitter mirror) for ticker mentions.
    Searches configured Twitter accounts for mentions.
    """
    if nitter_instances is None:
        nitter_instances = [
            "nitter.privacydev.net",
            "nitter.poast.org",
        ]

    config_path = Path(__file__).parent.parent.parent / "config" / "sources.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)

    twitter_accounts = config.get('twitter', [])
    results = []
    cutoff = datetime.now() - timedelta(days=days_back)

    for account in twitter_accounts:
        handle = account.get('handle', '').replace('@', '')
        if not handle:
            continue

        for instance in nitter_instances:
            try:
                rss_url = f"https://{instance}/{handle}/rss"
                feed = feedparser.parse(rss_url, timeout=10)

                if not feed.entries:
                    continue

                for entry in feed.entries[:20]:
                    content = entry.get('title', '').upper()

                    # Check for ticker mention (with $ or standalone)
                    ticker_patterns = [
                        f"${ticker.upper()}",
                        f" {ticker.upper()} ",
                        f" {ticker.upper()}.",
                        f" {ticker.upper()},",
                    ]

                    if not any(p in f" {content} " for p in ticker_patterns):
                        continue

                    published = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        published = datetime(*entry.published_parsed[:6])

                    if published and published < cutoff:
                        continue

                    result = {
                        'source': f"@{handle}",
                        'title': entry.get('title', '')[:280],
                        'link': entry.get('link', ''),
                        'published': published.isoformat() if published else None,
                        'ticker': ticker,
                        'focus': account.get('focus', ''),
                    }
                    results.append(result)

                break  # Successful fetch, don't try other instances

            except Exception as e:
                continue  # Try next instance

    return results


def get_stock_price_info(ticker: str) -> Optional[dict]:
    """Get current price info using yfinance."""
    if yf is None:
        return None

    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        # Get recent price action
        hist = stock.history(period="5d")

        if hist.empty:
            return None

        current = hist['Close'].iloc[-1]
        prev = hist['Close'].iloc[-2] if len(hist) > 1 else current
        change_pct = ((current - prev) / prev) * 100

        # 5 day performance
        five_day_start = hist['Close'].iloc[0]
        five_day_change = ((current - five_day_start) / five_day_start) * 100

        return {
            'price': round(current, 2),
            'change_1d': round(change_pct, 2),
            'change_5d': round(five_day_change, 2),
            'market_cap': info.get('marketCap'),
            'pe_ratio': info.get('forwardPE'),
            '52w_high': info.get('fiftyTwoWeekHigh'),
            '52w_low': info.get('fiftyTwoWeekLow'),
        }
    except Exception as e:
        print(f"Error fetching price for {ticker}: {e}")
        return None


def search_all_sources_for_ticker(
    ticker: str,
    company_name: str,
    days_back: int = 1,
    include_price: bool = True
) -> dict:
    """
    Comprehensive search for a single ticker across all sources.
    """
    mentions = []

    # Search each source
    google_results = search_google_news(ticker, company_name, days_back)
    mentions.extend(google_results)

    substack_results = search_substack_for_ticker(ticker, days_back + 2)  # Wider window for Substacks
    mentions.extend(substack_results)

    twitter_results = search_nitter_for_ticker(ticker, days_back)
    mentions.extend(twitter_results)

    # Get price info
    price_info = get_stock_price_info(ticker) if include_price else None

    return {
        'ticker': ticker,
        'company_name': company_name,
        'mentions': mentions,
        'mention_count': len(mentions),
        'price_info': price_info,
        'sources_found': list(set(m['source'] for m in mentions)),
    }


def find_active_stocks(
    days_back: int = 1,
    min_mentions: int = 1,
    max_stocks: int = 20,
    include_prices: bool = True
) -> list[dict]:
    """
    Find the most active stocks from the watchlist.
    Returns stocks sorted by activity (number of mentions).
    """
    all_stocks = get_all_tickers()
    active_stocks = []

    print(f"Searching {len(all_stocks)} stocks for activity...")

    for i, stock in enumerate(all_stocks):
        ticker = stock['symbol']
        name = stock['name']

        if i > 0 and i % 20 == 0:
            print(f"  Processed {i}/{len(all_stocks)} stocks...")
            time.sleep(1)  # Rate limiting

        result = search_all_sources_for_ticker(
            ticker,
            name,
            days_back,
            include_price=include_prices
        )

        result['thesis'] = stock.get('thesis', '')
        result['category'] = stock.get('category', '')
        result['theme'] = stock.get('theme', '')

        if result['mention_count'] >= min_mentions:
            active_stocks.append(result)

    # Sort by activity
    active_stocks.sort(key=lambda x: x['mention_count'], reverse=True)

    return active_stocks[:max_stocks]


def generate_stock_summary(stock_data: dict) -> str:
    """
    Generate a text summary for a single stock's activity.
    """
    ticker = stock_data['ticker']
    name = stock_data['company_name']
    mentions = stock_data['mentions']
    price = stock_data.get('price_info', {})

    lines = []

    # Price header
    if price:
        change_emoji = "+" if price.get('change_1d', 0) >= 0 else ""
        lines.append(f"**{ticker}** ({name}) - ${price.get('price', 'N/A')} ({change_emoji}{price.get('change_1d', 0)}%)")
        if price.get('change_5d'):
            five_day_emoji = "+" if price['change_5d'] >= 0 else ""
            lines.append(f"  5-day: {five_day_emoji}{price['change_5d']}%")
    else:
        lines.append(f"**{ticker}** ({name})")

    lines.append(f"  Thesis: {stock_data.get('thesis', 'N/A')}")
    lines.append(f"  Mentions: {len(mentions)} across {len(stock_data.get('sources_found', []))} sources")
    lines.append("")

    # Top mentions
    if mentions:
        lines.append("  **What people are saying:**")
        for m in mentions[:5]:
            source = m['source']
            title = m['title'][:150]
            link = m.get('link', '')
            lines.append(f"  - [{source}] {title}")
            if link:
                lines.append(f"    {link}")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    print("Testing stock search...\n")

    # Test single stock
    result = search_all_sources_for_ticker("NVDA", "NVIDIA", days_back=2)
    print(f"NVDA mentions: {result['mention_count']}")
    print(f"Sources: {result['sources_found']}")

    if result['price_info']:
        print(f"Price: ${result['price_info']['price']}")

    for m in result['mentions'][:3]:
        print(f"  - [{m['source']}] {m['title'][:80]}...")
