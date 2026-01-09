"""
Daily AI Investing Report Generator
Aggregates content and generates an educational morning briefing
"""

import yaml
from datetime import datetime
from pathlib import Path
from typing import Optional
import json
import random

from src.fetchers import (
    fetch_all_substacks,
    fetch_all_podcasts,
    fetch_all_twitter,
)


def load_config() -> dict:
    """Load sources configuration."""
    config_path = Path(__file__).parent.parent / "config" / "sources.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


def format_substack_section(articles: list[dict]) -> str:
    """Format Substack articles for the report."""
    if not articles:
        return "_No new Substack articles today._\n"

    lines = []
    for article in articles[:10]:  # Limit to 10
        must_read = "🔥 " if article.get('must_read') else ""
        lines.append(f"### {must_read}{article['source_name']}")
        lines.append(f"**{article['title']}**")
        lines.append(f"- Focus: {article.get('focus', 'N/A')}")
        lines.append(f"- [Read Article]({article['link']})")
        if article.get('summary'):
            summary = article['summary'][:300].replace('\n', ' ')
            lines.append(f"- Preview: {summary}...")
        lines.append("")

    return "\n".join(lines)


def format_podcast_section(episodes: list[dict]) -> str:
    """Format podcast episodes for the report."""
    if not episodes:
        return "_No new podcast episodes this week._\n"

    lines = []
    for ep in episodes[:8]:
        stocks = ep.get('stocks_mentioned', [])
        stock_badge = f" `{', '.join(stocks)}`" if stocks else ""
        lines.append(f"### {ep['podcast_name']}{stock_badge}")
        lines.append(f"**{ep['title']}**")
        lines.append(f"- Hosts: {ep.get('hosts', 'N/A')}")
        lines.append(f"- Why listen: {ep.get('why_listen', 'N/A')}")
        if ep.get('duration'):
            lines.append(f"- Duration: {ep['duration']}")
        lines.append(f"- [Listen]({ep['link']})")
        lines.append("")

    return "\n".join(lines)


def format_twitter_section(posts: list[dict]) -> str:
    """Format Twitter highlights for the report."""
    if not posts:
        return """_No curated Twitter highlights today._

**To add Twitter highlights:**
1. Throughout the day, save interesting AI investing tweets
2. Add them to `data/twitter_highlights.json`
3. Include the reasoning for why they matter
"""

    lines = []
    for post in posts[:10]:
        lines.append(f"### {post['handle']}")
        lines.append(f"> {post['content'][:280]}")
        if post.get('reasoning'):
            lines.append(f"- **Why it matters:** {post['reasoning']}")
        if post.get('stocks_mentioned'):
            lines.append(f"- Stocks: `{', '.join(post['stocks_mentioned'])}`")
        lines.append(f"- [View Tweet]({post['link']})")
        lines.append("")

    return "\n".join(lines)


def generate_learning_questions(config: dict) -> str:
    """
    Generate educational questions based on frameworks.
    These help build investing intuition over time.
    """
    frameworks = config.get('learning_frameworks', {})

    # General thinking questions
    general_questions = [
        "What's the bull case you found most compelling today? What's the strongest counter-argument?",
        "Which company mentioned today has the strongest moat? Why?",
        "If you had to buy one stock from today's report and hold for 5 years, which would it be and why?",
        "What's the biggest risk to AI investments that wasn't discussed?",
        "Which valuation seems most stretched? Which seems most reasonable?",
    ]

    # Framework-based questions
    framework_questions = [
        "Using the 'right to win' framework: Which company has the clearest path to AI dominance?",
        "Consider 'picks and shovels' vs 'direct AI bets': Which approach is better right now?",
        "Apply the Rule of 40: Which SaaS/AI company offers the best growth/profitability balance?",
        "Think about data moats: Who has the most defensible data advantage?",
        "What's priced in? Pick one stock and steelman why current prices already reflect the upside.",
    ]

    # Stock-specific questions
    specific_questions = [
        "NVIDIA vs AMD: What would need to happen for AMD to close the gap?",
        "Microsoft vs Google in AI: Who has the better strategy? Why?",
        "Palantir vs Snowflake: Which is the better AI platform bet?",
        "Compare two chip companies: ASML vs TSMC. Different parts of the stack - which is better positioned?",
        "Meta's open-source AI strategy: Brilliant or giving away the farm?",
    ]

    # Select questions
    selected = [
        random.choice(general_questions),
        random.choice(framework_questions),
        random.choice(specific_questions),
    ]

    lines = ["## 📝 Today's Learning Questions\n"]
    lines.append("*Answer these to sharpen your investing intuition. Log your responses!*\n")

    for i, q in enumerate(selected, 1):
        lines.append(f"**Q{i}:** {q}\n")

    lines.append("---")
    lines.append("*Record your answers using: `python -m src.pick_tracker respond`*")

    return "\n".join(lines)


def generate_watchlist_status(config: dict) -> str:
    """Generate a quick watchlist status section."""
    watchlist = config.get('watchlist', {})

    lines = ["## 📊 Watchlist Quick Reference\n"]

    for category, stocks in watchlist.items():
        if not isinstance(stocks, list):
            continue

        category_name = category.replace('_', ' ').title()
        lines.append(f"### {category_name}")

        for stock in stocks[:6]:  # Limit per category
            lines.append(f"- **{stock['symbol']}** ({stock['name']}): {stock['thesis']}")

        lines.append("")

    return "\n".join(lines)


def generate_daily_report(
    days_back_articles: int = 1,
    days_back_podcasts: int = 7,
    output_path: Optional[Path] = None,
) -> str:
    """
    Generate the complete daily morning report.

    Args:
        days_back_articles: Days to look back for articles
        days_back_podcasts: Days to look back for podcasts
        output_path: Optional path to save the report

    Returns:
        The complete report as markdown string
    """
    config = load_config()
    today = datetime.now().strftime("%Y-%m-%d")
    weekday = datetime.now().strftime("%A")

    # Fetch content
    articles = fetch_all_substacks(days_back_articles)
    podcasts = fetch_all_podcasts(days_back_podcasts)
    twitter = fetch_all_twitter(days_back_articles)

    # Build report
    report_lines = [
        f"# 🌅 AI Investing Morning Brief",
        f"**{weekday}, {today}**\n",
        "---\n",

        "## 📰 Substack Highlights\n",
        format_substack_section(articles),

        "---\n",

        "## 🎙️ Recent Podcasts\n",
        format_podcast_section(podcasts),

        "---\n",

        "## 🐦 Twitter Insights\n",
        format_twitter_section(twitter),

        "---\n",

        generate_watchlist_status(config),

        "---\n",

        generate_learning_questions(config),

        "\n---\n",

        "## 📈 Make Your Picks\n",
        "Based on today's report, log your investment thesis:\n",
        "```bash",
        'python -m src.pick_tracker add NVDA "buy" "Strong datacenter growth, AI training demand" --timeframe "6mo"',
        "```\n",

        "---",
        f"*Report generated: {datetime.now().isoformat()}*",
    ]

    report = "\n".join(report_lines)

    # Save report
    if output_path is None:
        output_path = Path(__file__).parent.parent / "data" / "reports" / f"report_{today}.md"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(report)

    print(f"Report saved to: {output_path}")

    return report


if __name__ == "__main__":
    print("Generating daily AI investing report...\n")
    report = generate_daily_report()
    print("\n" + "="*50 + "\n")
    print(report)
