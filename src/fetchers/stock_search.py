"""
Twitter-First Stock Social Search (v2 - Optimized)

Key optimizations over v1:
- Fetches each RSS feed ONCE, then scans for all tickers (was: per-ticker fetching)
- Uses concurrent.futures for parallel fetching
- Twitter-first: Shows actual takes/content, not just mentions

To rollback: cp src/fetchers/stock_search_v1_backup.py src/fetchers/stock_search.py
"""

import feedparser
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import yaml
import re
import time

try:
    import yfinance as yf
except ImportError:
    yf = None


def load_config() -> dict:
    """Load sources configuration."""
    config_path = Path(__file__).parent.parent.parent / "config" / "sources.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


def get_all_tickers() -> list[dict]:
    """Get flat list of all tickers with their info."""
    config = load_config()
    watchlist = config.get('watchlist', {})
    all_stocks = []

    for category, stocks in watchlist.items():
        if not isinstance(stocks, list):
            continue
        for stock in stocks:
            stock['category'] = category
            all_stocks.append(stock)

    return all_stocks


def get_ticker_set() -> set[str]:
    """Get set of all ticker symbols for fast lookup."""
    return {s['symbol'].upper() for s in get_all_tickers()}


def build_stock_patterns() -> dict[str, list[str]]:
    """
    Build comprehensive patterns for each stock including:
    - Ticker ($NVDA, NVDA)
    - Company name (Nvidia, NVIDIA)
    - Common variations/misspellings
    """
    stocks = get_all_tickers()
    patterns = {}

    # Manual additions for tricky names
    name_variations = {
        'NVDA': ['nvidia', 'nvda', 'jensen', 'geforce', 'cuda'],
        'AMD': ['amd', 'advanced micro', 'lisa su', 'ryzen', 'epyc', 'mi300', 'mi400'],
        'INTC': ['intel', 'intc', 'pat gelsinger', 'gaudi'],
        'TSM': ['tsmc', 'taiwan semi', 'taiwan semiconductor'],
        'ASML': ['asml', 'euv', 'lithography'],
        'AVGO': ['broadcom', 'avgo', 'hock tan'],
        'MU': ['micron', 'hbm', 'high bandwidth memory'],
        'MSFT': ['microsoft', 'msft', 'satya', 'azure', 'copilot'],
        'GOOGL': ['google', 'alphabet', 'deepmind', 'gemini', 'sundar'],
        'AMZN': ['amazon', 'aws', 'bedrock', 'trainium', 'inferentia'],
        'META': ['meta', 'facebook', 'zuckerberg', 'llama'],
        'AAPL': ['apple', 'aapl', 'tim cook', 'iphone'],
        'PLTR': ['palantir', 'pltr', 'alex karp', 'aip'],
        'SMCI': ['supermicro', 'super micro', 'smci'],
        'VRT': ['vertiv', 'vrt', 'cooling'],
        'ANET': ['arista', 'anet'],
        'MRVL': ['marvell', 'mrvl'],
        'ARM': ['arm', 'arm holdings', 'softbank'],
        'CRWD': ['crowdstrike', 'crwd'],
        'PANW': ['palo alto', 'panw'],
        'SNOW': ['snowflake', 'snow'],
        'CRM': ['salesforce', 'crm', 'agentforce'],
        'NOW': ['servicenow', 'now'],
        'ORCL': ['oracle', 'orcl', 'larry ellison'],
        'DELL': ['dell', 'dell technologies'],
        'HPE': ['hpe', 'hewlett packard'],
        'QCOM': ['qualcomm', 'qcom', 'snapdragon'],
        'LRCX': ['lam research', 'lrcx', 'lam'],
        'AMAT': ['applied materials', 'amat'],
        'KLAC': ['kla', 'klac'],
        'OKLO': ['oklo', 'nuclear', 'sam altman oklo'],
        'SMR': ['nuscale', 'smr', 'small modular'],
        'VST': ['vistra', 'vst'],
        'CEG': ['constellation', 'ceg', 'constellation energy'],
        'TSLA': ['tesla', 'tsla', 'elon', 'optimus', 'robotaxi', 'fsd'],
        'RKLB': ['rocket lab', 'rklb', 'neutron'],
        'ASTS': ['ast spacemobile', 'asts', 'sat to phone'],
        'IONQ': ['ionq', 'quantum', 'trapped ion'],
        'RGTI': ['rigetti', 'rgti'],
        'ALAB': ['astera', 'alab', 'astera labs'],
        'CRDO': ['credo', 'crdo'],
        'IREN': ['iris energy', 'iren'],
        'WULF': ['terawulf', 'wulf'],
        'CIFR': ['cipher', 'cifr', 'cipher mining'],
        'NBIS': ['nebius', 'nbis'],
        'CRWV': ['coreweave', 'crwv'],
        'GEV': ['ge vernova', 'gev', 'vernova'],
        'ISRG': ['intuitive', 'isrg', 'da vinci', 'davinci'],
        'SYM': ['symbotic', 'sym'],
        'PATH': ['uipath', 'path'],
        'DDOG': ['datadog', 'ddog'],
        'NET': ['cloudflare', 'net'],
        'ZS': ['zscaler', 'zs'],
        'MDB': ['mongodb', 'mdb', 'mongo'],
        'HOOD': ['robinhood', 'hood'],
        'SOFI': ['sofi', 'sofi technologies'],
    }

    for stock in stocks:
        ticker = stock['symbol'].upper()
        name = stock.get('name', '').lower()

        # Start with ticker patterns
        stock_patterns = [ticker.lower(), f"${ticker.lower()}"]

        # Add company name (split into words for partial matching)
        if name:
            stock_patterns.append(name)
            # Also add without common suffixes
            for suffix in [' inc', ' corp', ' ltd', ' holdings', ' technologies', ' semiconductor']:
                if name.endswith(suffix):
                    stock_patterns.append(name.replace(suffix, '').strip())

        # Add manual variations
        if ticker in name_variations:
            stock_patterns.extend(name_variations[ticker])

        patterns[ticker] = list(set(stock_patterns))

    return patterns


# AI/Semi keywords that make content relevant even without specific stock mentions
RELEVANCE_KEYWORDS = [
    # Hardware/Chips
    'gpu', 'gpus', 'chip', 'chips', 'semiconductor', 'semis', 'silicon',
    'hbm', 'memory', 'dram', 'nand', 'cowos', 'packaging', 'foundry',
    'asic', 'asics', 'fpga', 'accelerator', 'tpu', 'inference', 'training',
    # AI/ML
    'ai ', ' ai', 'artificial intelligence', 'machine learning', 'llm', 'llms',
    'gpt', 'transformer', 'neural', 'deep learning', 'model', 'models',
    'agentic', 'agent', 'agents', 'rag', 'fine-tun', 'embeddings',
    # Supply/Demand
    'supply', 'demand', 'shortage', 'glut', 'capacity', 'backlog', 'lead time',
    'capex', 'spending', 'buildout', 'datacenter', 'data center', 'hyperscaler',
    # Investment
    'stock', 'stocks', 'invest', 'bull', 'bear', 'long', 'short', 'buy', 'sell',
    'undervalued', 'overvalued', 'valuation', 'earnings', 'revenue', 'margin',
    'interesting', 'opportunity', 'thesis', 'position', 'accumulate',
    # Power/Infra
    'power', 'energy', 'nuclear', 'grid', 'cooling', 'electricity',
    # Specific tech
    'blackwell', 'hopper', 'grace', 'mi300', 'mi400', 'gaudi',
    'inference', 'training', 'scaling', 'compute', 'flops',
]


def extract_tickers_from_text(text: str, stock_patterns: dict[str, list[str]]) -> list[str]:
    """
    Find which stocks from our watchlist are mentioned in text.
    Matches tickers, company names, and variations.
    """
    if not text:
        return []

    text_lower = f" {text.lower()} "
    found = []

    for ticker, patterns in stock_patterns.items():
        for pattern in patterns:
            # Check for pattern with word boundaries
            search_patterns = [
                f" {pattern} ",
                f" {pattern}.",
                f" {pattern},",
                f" {pattern}:",
                f" {pattern}!",
                f" {pattern}?",
                f" {pattern}'",
                f"({pattern})",
                f"${pattern}",  # Cashtag
            ]
            if any(p in text_lower for p in search_patterns):
                found.append(ticker)
                break  # Found this ticker, move to next

    return found


def is_relevant_content(text: str) -> bool:
    """Check if content is relevant to AI/semi investing even without ticker mentions."""
    if not text:
        return False

    text_lower = text.lower()
    matches = sum(1 for kw in RELEVANCE_KEYWORDS if kw in text_lower)
    return matches >= 2  # Require at least 2 keyword matches


def classify_sentiment(text: str) -> str:
    """
    Basic sentiment classification from text.
    Returns: 'bullish', 'bearish', or 'neutral'
    """
    text_lower = text.lower()

    bullish_words = [
        'bull', 'long', 'buy', 'bullish', 'moon', 'rip', 'breakout',
        'accumulate', 'undervalued', 'upside', 'beat', 'crush', 'strong',
        'growth', 'opportunity', 'love', 'adding', 'bought', 'buying',
    ]

    bearish_words = [
        'bear', 'short', 'sell', 'bearish', 'dump', 'overvalued',
        'downside', 'miss', 'weak', 'concern', 'worried', 'sold',
        'selling', 'puts', 'crash', 'avoid', 'stay away', 'red flag',
    ]

    bull_count = sum(1 for w in bullish_words if w in text_lower)
    bear_count = sum(1 for w in bearish_words if w in text_lower)

    if bull_count > bear_count:
        return 'bullish'
    elif bear_count > bull_count:
        return 'bearish'
    return 'neutral'


def fetch_nitter_feed(handle: str, nitter_instances: list[str] = None) -> list[dict]:
    """
    Fetch tweets from a single Twitter handle via Nitter.
    Returns list of tweets with full content.
    """
    if nitter_instances is None:
        nitter_instances = [
            "nitter.privacydev.net",
            "nitter.poast.org",
            "nitter.cz",
        ]

    clean_handle = handle.replace("@", "")

    for instance in nitter_instances:
        try:
            rss_url = f"https://{instance}/{clean_handle}/rss"
            feed = feedparser.parse(rss_url, request_headers={'User-Agent': 'Mozilla/5.0'})

            if not feed.entries:
                continue

            tweets = []
            for entry in feed.entries[:30]:  # Get more tweets per account
                published = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6])

                tweet = {
                    'handle': f"@{clean_handle}",
                    'content': entry.get('title', ''),
                    'link': entry.get('link', ''),
                    'published': published,
                    'source_type': 'twitter',
                }
                tweets.append(tweet)

            return tweets

        except Exception as e:
            continue  # Try next instance

    return []


def fetch_substack_feed(substack: dict) -> list[dict]:
    """Fetch articles from a single Substack."""
    rss_url = substack.get('rss')
    if not rss_url:
        return []

    try:
        feed = feedparser.parse(rss_url)
        articles = []

        for entry in feed.entries[:10]:
            published = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                published = datetime(*entry.published_parsed[:6])

            article = {
                'source': substack.get('name', 'Substack'),
                'title': entry.get('title', ''),
                'content': entry.get('summary', ''),
                'link': entry.get('link', ''),
                'published': published,
                'source_type': 'substack',
                'must_read': substack.get('must_read', False),
            }
            articles.append(article)

        return articles

    except Exception as e:
        print(f"Error fetching {substack.get('name')}: {e}")
        return []


def fetch_all_twitter_content(days_back: int = 1) -> list[dict]:
    """
    Fetch all Twitter content from configured accounts in PARALLEL.
    Returns all tweets, ready to be scanned for tickers.
    """
    config = load_config()
    twitter_accounts = config.get('twitter', [])
    all_tweets = []
    cutoff = datetime.now() - timedelta(days=days_back)

    print(f"  Fetching {len(twitter_accounts)} Twitter accounts in parallel...")

    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_handle = {
            executor.submit(fetch_nitter_feed, acc.get('handle', '')): acc
            for acc in twitter_accounts
        }

        for future in as_completed(future_to_handle):
            account = future_to_handle[future]
            try:
                tweets = future.result()
                # Add account metadata and filter by date
                for tweet in tweets:
                    if tweet['published'] and tweet['published'] < cutoff:
                        continue
                    tweet['focus'] = account.get('focus', '')
                    tweet['why_follow'] = account.get('why_follow', '')
                    all_tweets.append(tweet)
            except Exception as e:
                print(f"  Error fetching {account.get('handle')}: {e}")

    print(f"  Got {len(all_tweets)} tweets from {len(twitter_accounts)} accounts")
    return all_tweets


def fetch_all_substack_content(days_back: int = 3) -> list[dict]:
    """
    Fetch all Substack content in PARALLEL.
    Returns all articles, ready to be scanned for tickers.
    """
    config = load_config()
    substacks = config.get('substacks', [])
    all_articles = []
    cutoff = datetime.now() - timedelta(days=days_back)

    print(f"  Fetching {len(substacks)} Substacks in parallel...")

    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_sub = {
            executor.submit(fetch_substack_feed, sub): sub
            for sub in substacks
        }

        for future in as_completed(future_to_sub):
            try:
                articles = future.result()
                for article in articles:
                    if article['published'] and article['published'] < cutoff:
                        continue
                    all_articles.append(article)
            except Exception as e:
                pass

    print(f"  Got {len(all_articles)} articles from {len(substacks)} Substacks")
    return all_articles


def scan_content_for_tickers(
    content_list: list[dict],
    stock_patterns: dict[str, list[str]],
    content_key: str = 'content'
) -> tuple[dict[str, list[dict]], list[dict]]:
    """
    Scan all content for stock mentions using comprehensive patterns.
    Returns:
        - dict mapping ticker -> list of mentions
        - list of relevant content without specific ticker mentions
    """
    mentions_by_ticker = {ticker: [] for ticker in stock_patterns.keys()}
    relevant_general = []  # Content relevant to AI/semis but no specific ticker

    for item in content_list:
        text = item.get(content_key, '') + ' ' + item.get('title', '')
        found_tickers = extract_tickers_from_text(text, stock_patterns)

        if found_tickers:
            for ticker in found_tickers:
                mention = item.copy()
                mention['sentiment'] = classify_sentiment(text)
                mention['matched_tickers'] = found_tickers
                mentions_by_ticker[ticker].append(mention)
        elif is_relevant_content(text):
            # No specific ticker but relevant to AI/semis
            item_copy = item.copy()
            item_copy['sentiment'] = classify_sentiment(text)
            item_copy['relevance'] = 'general_ai_semi'
            relevant_general.append(item_copy)

    return mentions_by_ticker, relevant_general


def get_stock_prices_batch(tickers: list[str]) -> dict[str, dict]:
    """
    Fetch prices for multiple tickers efficiently.
    """
    if yf is None:
        return {}

    prices = {}
    print(f"  Fetching prices for {len(tickers)} active stocks...")

    try:
        # yfinance can handle multiple tickers at once
        data = yf.download(
            tickers,
            period="5d",
            group_by='ticker',
            progress=False,
            threads=True
        )

        for ticker in tickers:
            try:
                if len(tickers) == 1:
                    hist = data
                else:
                    hist = data[ticker] if ticker in data.columns.get_level_values(0) else None

                if hist is None or hist.empty:
                    continue

                close = hist['Close'].dropna()
                if len(close) < 2:
                    continue

                current = close.iloc[-1]
                prev = close.iloc[-2]
                first = close.iloc[0]

                prices[ticker] = {
                    'price': round(float(current), 2),
                    'change_1d': round(((current - prev) / prev) * 100, 2),
                    'change_5d': round(((current - first) / first) * 100, 2),
                }
            except Exception:
                continue

    except Exception as e:
        print(f"  Price fetch error: {e}")

    return prices


def find_active_stocks(
    days_back: int = 1,  # 24 hours by default
    min_mentions: int = 1,
    max_stocks: int = 20,
    include_prices: bool = True,
    include_google_news: bool = False,  # Disabled by default for speed
) -> tuple[list[dict], list[dict]]:
    """
    Find stocks with Twitter/social activity - OPTIMIZED VERSION.

    Key optimization: Fetches all feeds ONCE, then scans for all tickers.
    Now uses comprehensive matching: tickers, company names, keywords.

    Returns:
        - List of active stocks with mentions
        - List of general relevant content (AI/semi discussion without specific tickers)
    """
    start_time = time.time()

    # Get all tickers and build comprehensive patterns
    all_stocks = get_all_tickers()
    ticker_to_info = {s['symbol'].upper(): s for s in all_stocks}
    stock_patterns = build_stock_patterns()

    print(f"Scanning {len(stock_patterns)} stocks with comprehensive pattern matching...")
    print(f"  (matching tickers, company names, CEO names, product names...)")

    # Fetch all content ONCE (the key optimization)
    twitter_content = fetch_all_twitter_content(days_back)
    substack_content = fetch_all_substack_content(days_back)

    # Scan for ticker mentions using comprehensive patterns
    print("  Scanning content for stock mentions...")
    twitter_mentions, twitter_general = scan_content_for_tickers(twitter_content, stock_patterns)
    substack_mentions, substack_general = scan_content_for_tickers(substack_content, stock_patterns, 'content')

    # Combine general relevant content
    general_relevant = twitter_general + substack_general

    # Build results for stocks with mentions
    active_stocks = []

    for ticker in stock_patterns.keys():
        twitter_hits = twitter_mentions.get(ticker, [])
        substack_hits = substack_mentions.get(ticker, [])

        total_mentions = len(twitter_hits) + len(substack_hits)
        if total_mentions < min_mentions:
            continue

        stock_info = ticker_to_info.get(ticker, {})

        result = {
            'ticker': ticker,
            'company_name': stock_info.get('name', ticker),
            'thesis': stock_info.get('thesis', ''),
            'category': stock_info.get('category', ''),
            'theme': stock_info.get('theme', ''),
            'twitter_mentions': twitter_hits,
            'substack_mentions': substack_hits,
            'mention_count': total_mentions,
            'twitter_count': len(twitter_hits),
        }
        active_stocks.append(result)

    # Sort by Twitter mentions first (user priority), then total
    active_stocks.sort(key=lambda x: (x['twitter_count'], x['mention_count']), reverse=True)
    active_stocks = active_stocks[:max_stocks]

    # Fetch prices only for active stocks
    if include_prices and active_stocks:
        active_tickers = [s['ticker'] for s in active_stocks]
        prices = get_stock_prices_batch(active_tickers)
        for stock in active_stocks:
            stock['price_info'] = prices.get(stock['ticker'])

    elapsed = time.time() - start_time
    print(f"  Done! Found {len(active_stocks)} active stocks + {len(general_relevant)} general takes in {elapsed:.1f}s")

    return active_stocks, general_relevant


def search_all_sources_for_ticker(
    ticker: str,
    company_name: str,
    days_back: int = 2,
    include_price: bool = True
) -> dict:
    """
    Search for a single ticker (for compatibility).
    Note: For bulk searches, use find_active_stocks() instead.
    """
    stock_patterns = {ticker.upper(): [ticker.lower(), company_name.lower()]}

    twitter_content = fetch_all_twitter_content(days_back)
    twitter_mentions, _ = scan_content_for_tickers(twitter_content, stock_patterns)

    mentions = twitter_mentions.get(ticker.upper(), [])

    price_info = None
    if include_price:
        prices = get_stock_prices_batch([ticker])
        price_info = prices.get(ticker)

    return {
        'ticker': ticker,
        'company_name': company_name,
        'mentions': mentions,
        'mention_count': len(mentions),
        'price_info': price_info,
    }


def generate_stock_summary(stock_data: dict) -> str:
    """Generate text summary for a stock's Twitter activity."""
    ticker = stock_data['ticker']
    name = stock_data['company_name']
    twitter_mentions = stock_data.get('twitter_mentions', [])
    price = stock_data.get('price_info', {})

    lines = []

    # Price header
    if price:
        change = price.get('change_1d', 0)
        sign = "+" if change >= 0 else ""
        lines.append(f"**{ticker}** ({name}) - ${price.get('price', 'N/A')} ({sign}{change}%)")
    else:
        lines.append(f"**{ticker}** ({name})")

    lines.append(f"  Thesis: {stock_data.get('thesis', 'N/A')}")

    if twitter_mentions:
        # Count sentiment
        bullish = sum(1 for m in twitter_mentions if m.get('sentiment') == 'bullish')
        bearish = sum(1 for m in twitter_mentions if m.get('sentiment') == 'bearish')

        lines.append(f"  Twitter: {len(twitter_mentions)} takes ({bullish} bullish, {bearish} bearish)")
        lines.append("")
        lines.append("  **Key takes:**")

        for m in twitter_mentions[:4]:
            handle = m.get('handle', 'Unknown')
            content = m.get('content', '')[:200]
            sentiment = m.get('sentiment', 'neutral')
            emoji = "🟢" if sentiment == 'bullish' else "🔴" if sentiment == 'bearish' else "⚪"
            lines.append(f"  {emoji} {handle}: \"{content}\"")

    return "\n".join(lines)


if __name__ == "__main__":
    print("Testing optimized stock search...\n")
    active = find_active_stocks(days_back=2, max_stocks=10)

    for stock in active[:5]:
        print(f"\n{stock['ticker']} - {stock['mention_count']} mentions")
        for m in stock.get('twitter_mentions', [])[:2]:
            print(f"  @{m['handle']}: {m['content'][:100]}...")
