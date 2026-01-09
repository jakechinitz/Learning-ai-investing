"""
Stock-Centric Daily AI Investing Report
Searches across social media and news for what people are saying about your stocks
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


def format_stock_section(stock_data: dict) -> str:
    """Format a single stock's activity section."""
    ticker = stock_data['ticker']
    name = stock_data['company_name']
    mentions = stock_data.get('mentions', [])
    price_info = stock_data.get('price_info')
    thesis = stock_data.get('thesis', '')

    lines = []

    # Header with price
    price_badge = format_price_badge(price_info)
    lines.append(f"### {ticker} - {name} {price_badge}")

    # 5-day context if available
    if price_info and price_info.get('change_5d'):
        five_day = price_info['change_5d']
        sign = "+" if five_day >= 0 else ""
        lines.append(f"*5-day: {sign}{five_day:.1f}%*")

    lines.append("")

    # Investment thesis reminder
    if thesis:
        lines.append(f"**Thesis:** {thesis}")
        lines.append("")

    # What people are saying
    if mentions:
        lines.append(f"**{len(mentions)} mentions found:**")
        lines.append("")

        for m in mentions[:6]:  # Show top 6
            source = m['source']
            title = m.get('title', '')[:200]
            link = m.get('link', '')

            if link:
                lines.append(f"- **[{source}]** [{title}]({link})")
            else:
                lines.append(f"- **[{source}]** {title}")

        lines.append("")

    return "\n".join(lines)


def format_quick_movers(active_stocks: list[dict]) -> str:
    """Format a quick summary of price movers."""
    lines = ["## Quick Movers\n"]

    gainers = []
    losers = []

    for stock in active_stocks:
        price_info = stock.get('price_info')
        if not price_info:
            continue

        change = price_info.get('change_1d', 0)
        if change >= 2:
            gainers.append((stock['ticker'], change, stock['company_name']))
        elif change <= -2:
            losers.append((stock['ticker'], change, stock['company_name']))

    if gainers:
        gainers.sort(key=lambda x: x[1], reverse=True)
        lines.append("**Top Gainers:**")
        for ticker, change, name in gainers[:5]:
            lines.append(f"- {ticker} ({name}): +{change:.1f}%")
        lines.append("")

    if losers:
        losers.sort(key=lambda x: x[1])
        lines.append("**Notable Drops:**")
        for ticker, change, name in losers[:5]:
            lines.append(f"- {ticker} ({name}): {change:.1f}%")
        lines.append("")

    if not gainers and not losers:
        lines.append("*No major moves today (>2%)*\n")

    return "\n".join(lines)


def format_category_breakdown(active_stocks: list[dict]) -> str:
    """Group active stocks by category/theme."""
    by_category = {}

    for stock in active_stocks:
        cat = stock.get('category', 'other')
        theme = stock.get('theme', '')
        key = theme if theme else cat.replace('_', ' ').title()

        if key not in by_category:
            by_category[key] = []
        by_category[key].append(stock)

    lines = ["## Activity by Theme\n"]

    for category, stocks in sorted(by_category.items()):
        tickers = [s['ticker'] for s in stocks[:8]]
        lines.append(f"**{category}:** {', '.join(tickers)}")

    lines.append("")
    return "\n".join(lines)


def generate_learning_questions(active_stocks: list[dict]) -> str:
    """Generate questions based on today's active stocks."""
    lines = ["## Learning Questions\n"]
    lines.append("*Sharpen your thinking - respond to log your analysis*\n")

    # Dynamic questions based on active stocks
    if active_stocks:
        top_stock = active_stocks[0]
        ticker = top_stock['ticker']
        name = top_stock['company_name']

        questions = [
            f"**Q1:** {ticker} ({name}) had the most discussion today. What's driving the conversation? Is the sentiment bullish or bearish?",
            f"**Q2:** Of the stocks with activity today, which one do you think offers the best risk/reward at current prices? Why?",
            f"**Q3:** Pick one stock from today's report. What would need to happen for you to buy (or sell) it tomorrow?",
        ]
    else:
        questions = [
            "**Q1:** No major stock-specific news today. Is that bullish (market digesting gains) or concerning (losing momentum)?",
            "**Q2:** Without news flow, what stocks on your watchlist would you research deeper today?",
            "**Q3:** What macro factors are you watching that could impact your AI/tech positions?",
        ]

    for q in questions:
        lines.append(q)
        lines.append("")

    return "\n".join(lines)


def format_recent_content(days_back: int = 3) -> str:
    """Show recent must-read content from Substacks/Podcasts."""
    lines = ["## Recent Must-Read Content\n"]

    articles = fetch_all_substacks(days_back)
    podcasts = fetch_all_podcasts(days_back * 2)

    # Filter to must-reads
    must_reads = [a for a in articles if a.get('must_read')][:3]
    top_podcasts = podcasts[:2]

    if must_reads:
        lines.append("**Substacks:**")
        for a in must_reads:
            lines.append(f"- [{a['source_name']}] [{a['title']}]({a['link']})")
        lines.append("")

    if top_podcasts:
        lines.append("**Podcasts:**")
        for p in top_podcasts:
            lines.append(f"- [{p['podcast_name']}] {p['title']}")
        lines.append("")

    if not must_reads and not top_podcasts:
        lines.append("*No new must-read content today*\n")

    return "\n".join(lines)


def generate_daily_report(
    days_back: int = 1,
    max_stocks: int = 15,
    output_path: Optional[Path] = None,
) -> str:
    """
    Generate the stock-focused daily morning report.

    Searches for what people are saying about each stock in your watchlist
    and surfaces the most active/interesting discussions.
    """
    config = load_config()
    today = datetime.now().strftime("%Y-%m-%d")
    weekday = datetime.now().strftime("%A")

    print("Searching for stock activity across all sources...")
    print("This may take a few minutes...\n")

    # Find stocks with activity
    active_stocks = find_active_stocks(
        days_back=days_back,
        min_mentions=1,
        max_stocks=max_stocks,
        include_prices=True
    )

    total_stocks = len(get_all_tickers())
    active_count = len(active_stocks)

    # Build report
    report_lines = [
        f"# AI Investing Daily Brief",
        f"**{weekday}, {today}**\n",
        f"*Scanned {total_stocks} stocks. {active_count} with mentions today.*",
        "",
        "---\n",
    ]

    # Quick movers section (if we have price data)
    if active_stocks:
        report_lines.append(format_quick_movers(active_stocks))
        report_lines.append("---\n")

        # Theme breakdown
        report_lines.append(format_category_breakdown(active_stocks))
        report_lines.append("---\n")

        # Main stock-by-stock section
        report_lines.append("## What People Are Saying\n")

        for stock in active_stocks:
            report_lines.append(format_stock_section(stock))
            report_lines.append("---\n")

    else:
        report_lines.append("## No Major Activity Today\n")
        report_lines.append("*Your watchlist stocks weren't heavily discussed today.*")
        report_lines.append("*This could mean: consolidation phase, or worth checking prices for quiet accumulation.*\n")
        report_lines.append("---\n")

    # Recent must-read content
    report_lines.append(format_recent_content(days_back + 2))
    report_lines.append("---\n")

    # Learning questions
    report_lines.append(generate_learning_questions(active_stocks))
    report_lines.append("---\n")

    # Call to action
    report_lines.extend([
        "## Make Your Picks\n",
        "Reply with your thoughts and they'll be logged automatically.",
        "",
        "Example: *\"Bullish on NVDA, datacenter numbers look strong. Watching AMD for MI300 traction.\"*",
        "",
        "---",
        f"*Report generated: {datetime.now().isoformat()}*",
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
    print("Generating stock-focused daily report...\n")
    print("=" * 50)
    report = generate_daily_report()
    print("\n" + "=" * 50 + "\n")
    print(report)
