"""
Twitter-First Daily AI Investing Report (v2)
Shows actual Twitter takes and sentiment for your watchlist stocks

To rollback: cp src/report_generator_v1_backup.py src/report_generator.py
"""

import yaml
from datetime import datetime
from pathlib import Path
from typing import Optional
import random

from src.fetchers import (
    find_active_stocks,
    get_all_tickers,
    fetch_all_substacks,
    fetch_all_podcasts,
)


def load_config() -> dict:
    """Load sources configuration."""
    config_path = Path(__file__).parent.parent / "config" / "sources.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


def format_price_badge(price_info: dict) -> str:
    """Format price info as a compact badge."""
    if not price_info:
        return ""

    price = price_info.get('price', 0)
    change = price_info.get('change_1d', 0)

    if change >= 3:
        emoji = "🚀"
    elif change >= 1:
        emoji = "📈"
    elif change <= -3:
        emoji = "📉"
    elif change <= -1:
        emoji = "⬇️"
    else:
        emoji = "➡️"

    sign = "+" if change >= 0 else ""
    return f"{emoji} ${price:.2f} ({sign}{change:.1f}%)"


def format_twitter_take(mention: dict, include_link: bool = True) -> str:
    """Format a single Twitter take with sentiment indicator."""
    handle = mention.get('handle', 'Unknown')
    content = mention.get('content', '')
    sentiment = mention.get('sentiment', 'neutral')
    link = mention.get('link', '')

    # Sentiment emoji
    if sentiment == 'bullish':
        emoji = "🟢"
    elif sentiment == 'bearish':
        emoji = "🔴"
    else:
        emoji = "⚪"

    # Clean up content - remove extra whitespace, limit length
    content = ' '.join(content.split())[:280]

    line = f"{emoji} **{handle}**: \"{content}\""
    if include_link and link:
        line += f"\n   [View]({link})"

    return line


def format_stock_section(stock_data: dict) -> str:
    """Format a single stock's Twitter activity."""
    ticker = stock_data['ticker']
    name = stock_data['company_name']
    twitter_mentions = stock_data.get('twitter_mentions', [])
    substack_mentions = stock_data.get('substack_mentions', [])
    price_info = stock_data.get('price_info')
    thesis = stock_data.get('thesis', '')

    lines = []

    # Header with price
    price_badge = format_price_badge(price_info)
    lines.append(f"### {ticker} - {name} {price_badge}")

    # 5-day context
    if price_info and price_info.get('change_5d'):
        five_day = price_info['change_5d']
        sign = "+" if five_day >= 0 else ""
        lines.append(f"*5-day: {sign}{five_day:.1f}%*")

    lines.append("")

    # Thesis reminder
    if thesis:
        lines.append(f"**Your thesis:** {thesis}")
        lines.append("")

    # Twitter takes - the main focus
    if twitter_mentions:
        # Sentiment summary
        bullish = sum(1 for m in twitter_mentions if m.get('sentiment') == 'bullish')
        bearish = sum(1 for m in twitter_mentions if m.get('sentiment') == 'bearish')
        neutral = len(twitter_mentions) - bullish - bearish

        sentiment_summary = []
        if bullish:
            sentiment_summary.append(f"{bullish} bullish")
        if bearish:
            sentiment_summary.append(f"{bearish} bearish")
        if neutral:
            sentiment_summary.append(f"{neutral} neutral")

        lines.append(f"**Twitter** ({', '.join(sentiment_summary)}):")
        lines.append("")

        # Show actual takes
        for m in twitter_mentions[:5]:  # Top 5 takes
            lines.append(format_twitter_take(m, include_link=True))
            lines.append("")

    # Substack mentions (secondary)
    if substack_mentions:
        lines.append(f"**Substack** ({len(substack_mentions)} mentions):")
        for m in substack_mentions[:2]:
            source = m.get('source', 'Substack')
            title = m.get('title', '')[:100]
            link = m.get('link', '')
            lines.append(f"- [{source}] [{title}]({link})")
        lines.append("")

    return "\n".join(lines)


def format_sentiment_overview(active_stocks: list[dict]) -> str:
    """Create a quick sentiment overview across all stocks."""
    lines = ["## Sentiment Overview\n"]

    most_bullish = []
    most_bearish = []
    most_discussed = []

    for stock in active_stocks:
        twitter = stock.get('twitter_mentions', [])
        if not twitter:
            continue

        bullish = sum(1 for m in twitter if m.get('sentiment') == 'bullish')
        bearish = sum(1 for m in twitter if m.get('sentiment') == 'bearish')
        total = len(twitter)

        if total >= 2:
            bull_ratio = bullish / total
            bear_ratio = bearish / total

            if bull_ratio >= 0.6:
                most_bullish.append((stock['ticker'], bullish, total))
            if bear_ratio >= 0.6:
                most_bearish.append((stock['ticker'], bearish, total))

        most_discussed.append((stock['ticker'], total, stock['company_name']))

    # Most discussed
    most_discussed.sort(key=lambda x: x[1], reverse=True)
    if most_discussed:
        lines.append("**Most Discussed:**")
        for ticker, count, name in most_discussed[:5]:
            lines.append(f"- {ticker} ({name}): {count} takes")
        lines.append("")

    # Bullish sentiment
    if most_bullish:
        lines.append("**Bullish Sentiment:**")
        for ticker, bullish, total in most_bullish[:5]:
            lines.append(f"- {ticker}: {bullish}/{total} bullish")
        lines.append("")

    # Bearish sentiment
    if most_bearish:
        lines.append("**Bearish Sentiment:**")
        for ticker, bearish, total in most_bearish[:5]:
            lines.append(f"- {ticker}: {bearish}/{total} bearish")
        lines.append("")

    return "\n".join(lines)


def generate_dynamic_questions(active_stocks: list[dict]) -> str:
    """
    Generate questions specifically based on today's discussions.
    These should provoke real thinking about the takes seen.
    """
    lines = ["## Think About This\n"]

    if not active_stocks:
        lines.append("*No major discussions today. Good day to do your own research.*")
        return "\n".join(lines)

    questions = []

    # Find stocks with conflicting sentiment
    for stock in active_stocks:
        twitter = stock.get('twitter_mentions', [])
        if len(twitter) < 2:
            continue

        bullish = [m for m in twitter if m.get('sentiment') == 'bullish']
        bearish = [m for m in twitter if m.get('sentiment') == 'bearish']

        if bullish and bearish:
            bull_take = bullish[0].get('content', '')[:100]
            bear_take = bearish[0].get('content', '')[:100]
            questions.append(
                f"**{stock['ticker']} Debate:** Bulls say \"{bull_take}...\" "
                f"Bears say \"{bear_take}...\" Who's right and why?"
            )

    # Find the most discussed stock
    if active_stocks:
        top = active_stocks[0]
        twitter = top.get('twitter_mentions', [])
        if twitter:
            sample_take = twitter[0].get('content', '')[:150]
            questions.append(
                f"**{top['ticker']} is trending.** One take: \"{sample_take}\" "
                f"What's missing from this analysis? What would change your mind?"
            )

    # Find any stock with strong bullish sentiment - question the thesis
    for stock in active_stocks[:5]:
        twitter = stock.get('twitter_mentions', [])
        bullish = sum(1 for m in twitter if m.get('sentiment') == 'bullish')
        if len(twitter) >= 2 and bullish / len(twitter) >= 0.7:
            questions.append(
                f"**Consensus check:** {stock['ticker']} has {bullish}/{len(twitter)} bullish takes. "
                f"When everyone agrees, what are they missing? What's the bear case?"
            )
            break

    # Find any bearish stock - is it an opportunity?
    for stock in active_stocks[:5]:
        twitter = stock.get('twitter_mentions', [])
        bearish = sum(1 for m in twitter if m.get('sentiment') == 'bearish')
        if len(twitter) >= 2 and bearish / len(twitter) >= 0.6:
            questions.append(
                f"**Contrarian check:** {stock['ticker']} has {bearish}/{len(twitter)} bearish takes. "
                f"Is the crowd right, or is this capitulation/opportunity?"
            )
            break

    # Price vs sentiment disconnect
    for stock in active_stocks[:5]:
        price = stock.get('price_info', {})
        twitter = stock.get('twitter_mentions', [])
        if not price or not twitter:
            continue

        change = price.get('change_1d', 0)
        bullish = sum(1 for m in twitter if m.get('sentiment') == 'bullish')

        # Stock up but bearish sentiment, or down but bullish
        if change >= 2 and bullish < len(twitter) / 2:
            questions.append(
                f"**Disconnect:** {stock['ticker']} is up {change:.1f}% but sentiment is cautious. "
                f"Is the market wrong or are the tweeters wrong?"
            )
            break
        elif change <= -2 and bullish > len(twitter) / 2:
            questions.append(
                f"**Disconnect:** {stock['ticker']} is down {change:.1f}% but bulls are buying. "
                f"Catching a falling knife or smart accumulation?"
            )
            break

    # Limit to 3 questions, shuffle for variety
    random.shuffle(questions)
    for q in questions[:3]:
        lines.append(q)
        lines.append("")

    # Always add a synthesis question
    if len(active_stocks) >= 3:
        tickers = [s['ticker'] for s in active_stocks[:5]]
        lines.append(
            f"**Synthesis:** Looking at today's discussion across {', '.join(tickers)} - "
            f"what's the one insight that could actually make you money?"
        )
        lines.append("")

    return "\n".join(lines)


def format_quick_movers(active_stocks: list[dict]) -> str:
    """Format price movers with their sentiment."""
    lines = ["## Price + Sentiment\n"]

    movers = []
    for stock in active_stocks:
        price = stock.get('price_info')
        if not price:
            continue

        change = price.get('change_1d', 0)
        twitter = stock.get('twitter_mentions', [])
        bullish = sum(1 for m in twitter if m.get('sentiment') == 'bullish')
        bearish = sum(1 for m in twitter if m.get('sentiment') == 'bearish')

        movers.append({
            'ticker': stock['ticker'],
            'name': stock['company_name'],
            'change': change,
            'price': price.get('price', 0),
            'bullish': bullish,
            'bearish': bearish,
            'total': len(twitter),
        })

    movers.sort(key=lambda x: abs(x['change']), reverse=True)

    for m in movers[:8]:
        sign = "+" if m['change'] >= 0 else ""
        sentiment = ""
        if m['total'] > 0:
            sentiment = f" | {m['bullish']}🟢 {m['bearish']}🔴"
        lines.append(f"- **{m['ticker']}** ${m['price']:.2f} ({sign}{m['change']:.1f}%){sentiment}")

    lines.append("")
    return "\n".join(lines)


def generate_daily_report(
    days_back: int = 2,
    max_stocks: int = 15,
    output_path: Optional[Path] = None,
) -> str:
    """
    Generate Twitter-first daily report.
    Shows actual takes and sentiment from your followed accounts.
    """
    config = load_config()
    today = datetime.now().strftime("%Y-%m-%d")
    weekday = datetime.now().strftime("%A")

    print("Scanning for Twitter activity on your watchlist...")

    # Find stocks with activity
    active_stocks = find_active_stocks(
        days_back=days_back,
        min_mentions=1,
        max_stocks=max_stocks,
        include_prices=True
    )

    total_stocks = len(get_all_tickers())
    active_count = len(active_stocks)
    total_takes = sum(len(s.get('twitter_mentions', [])) for s in active_stocks)

    # Build report
    report_lines = [
        f"# AI Investing Brief",
        f"**{weekday}, {today}**\n",
        f"*{active_count} stocks with activity | {total_takes} Twitter takes found*",
        "",
        "---\n",
    ]

    if active_stocks:
        # Price + Sentiment overview
        report_lines.append(format_quick_movers(active_stocks))
        report_lines.append("---\n")

        # Sentiment overview
        report_lines.append(format_sentiment_overview(active_stocks))
        report_lines.append("---\n")

        # Main section: What people are saying
        report_lines.append("## What People Are Saying\n")

        for stock in active_stocks:
            if stock.get('twitter_mentions') or stock.get('substack_mentions'):
                report_lines.append(format_stock_section(stock))
                report_lines.append("---\n")

    else:
        report_lines.append("## Quiet Day\n")
        report_lines.append("*No significant Twitter activity on your watchlist stocks today.*\n")
        report_lines.append("---\n")

    # Dynamic questions based on actual content
    report_lines.append(generate_dynamic_questions(active_stocks))
    report_lines.append("---\n")

    # Call to action
    report_lines.extend([
        "## Your Turn\n",
        "Reply with your take. Examples:",
        "- *\"The NVDA bulls are missing the margin pressure from competition\"*",
        "- *\"Adding AMD here, the MI300 ramp is underappreciated\"*",
        "- *\"Staying away from SMCI until accounting clears up\"*",
        "",
        "---",
        f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | [Rollback: see backup files]*",
    ])

    report = "\n".join(report_lines)

    # Save report
    if output_path is None:
        output_path = Path(__file__).parent.parent / "data" / "reports" / f"report_{today}.md"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(report)

    print(f"\nReport saved to: {output_path}")

    return report


if __name__ == "__main__":
    print("Generating Twitter-first daily report...\n")
    print("=" * 50)
    report = generate_daily_report()
    print("\n" + "=" * 50 + "\n")
    print(report)
