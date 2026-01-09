"""
Stock Pick Tracker
Track your investment picks and measure performance over time.

Usage:
    python -m src.pick_tracker add NVDA buy "AI datacenter demand" --timeframe 6mo
    python -m src.pick_tracker list
    python -m src.pick_tracker performance
    python -m src.pick_tracker respond
    python -m src.pick_tracker journal "Learned about TSMC's moat today..."
"""

import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional
import sys

# Data file paths
DATA_DIR = Path(__file__).parent.parent / "data"
PICKS_FILE = DATA_DIR / "picks.json"
JOURNAL_FILE = DATA_DIR / "journal.json"
RESPONSES_FILE = DATA_DIR / "question_responses.json"


def ensure_data_files():
    """Ensure data directory and files exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not PICKS_FILE.exists():
        with open(PICKS_FILE, 'w') as f:
            json.dump({"picks": [], "version": "1.0"}, f, indent=2)

    if not JOURNAL_FILE.exists():
        with open(JOURNAL_FILE, 'w') as f:
            json.dump({"entries": []}, f, indent=2)

    if not RESPONSES_FILE.exists():
        with open(RESPONSES_FILE, 'w') as f:
            json.dump({"responses": []}, f, indent=2)


def load_picks() -> dict:
    """Load picks from file."""
    ensure_data_files()
    with open(PICKS_FILE) as f:
        return json.load(f)


def save_picks(data: dict):
    """Save picks to file."""
    with open(PICKS_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def add_pick(
    symbol: str,
    action: str,  # buy, sell, hold, watch
    thesis: str,
    timeframe: str = "unspecified",
    price: Optional[float] = None,
    confidence: str = "medium",  # low, medium, high
    catalyst: str = "",
) -> dict:
    """
    Add a new stock pick with investment thesis.

    Args:
        symbol: Stock ticker
        action: buy, sell, hold, or watch
        thesis: Your investment reasoning
        timeframe: Expected holding period
        price: Entry price (optional, fetched if not provided)
        confidence: Your conviction level
        catalyst: What would make you right/wrong

    Returns:
        The created pick record
    """
    data = load_picks()

    pick = {
        "id": len(data["picks"]) + 1,
        "symbol": symbol.upper(),
        "action": action.lower(),
        "thesis": thesis,
        "timeframe": timeframe,
        "entry_price": price,
        "confidence": confidence,
        "catalyst": catalyst,
        "created_at": datetime.now().isoformat(),
        "status": "active",  # active, closed, expired
        "exit_price": None,
        "exit_date": None,
        "exit_reason": None,
        "performance_pct": None,
    }

    data["picks"].append(pick)
    save_picks(data)

    print(f"✅ Added pick: {action.upper()} {symbol.upper()}")
    print(f"   Thesis: {thesis}")
    print(f"   Timeframe: {timeframe}")
    print(f"   Confidence: {confidence}")

    return pick


def list_picks(status: str = "active") -> list[dict]:
    """List all picks with optional status filter."""
    data = load_picks()
    picks = data["picks"]

    if status != "all":
        picks = [p for p in picks if p.get("status") == status]

    return picks


def close_pick(
    pick_id: int,
    exit_price: float,
    reason: str,
) -> dict:
    """
    Close out a pick and record the outcome.

    Args:
        pick_id: ID of the pick to close
        exit_price: Price at exit
        reason: Why you're closing (thesis played out, was wrong, etc.)

    Returns:
        The updated pick record
    """
    data = load_picks()

    for pick in data["picks"]:
        if pick["id"] == pick_id:
            pick["status"] = "closed"
            pick["exit_price"] = exit_price
            pick["exit_date"] = datetime.now().isoformat()
            pick["exit_reason"] = reason

            # Calculate performance if we have entry price
            if pick.get("entry_price"):
                if pick["action"] == "buy":
                    pick["performance_pct"] = (
                        (exit_price - pick["entry_price"]) / pick["entry_price"]
                    ) * 100
                elif pick["action"] == "sell":
                    pick["performance_pct"] = (
                        (pick["entry_price"] - exit_price) / pick["entry_price"]
                    ) * 100

            save_picks(data)
            print(f"✅ Closed pick #{pick_id}: {pick['symbol']}")
            if pick.get("performance_pct") is not None:
                pct = pick["performance_pct"]
                emoji = "📈" if pct > 0 else "📉"
                print(f"   {emoji} Performance: {pct:+.1f}%")
            return pick

    print(f"❌ Pick #{pick_id} not found")
    return {}


def get_performance_summary() -> dict:
    """Generate a performance summary of all picks."""
    data = load_picks()
    picks = data["picks"]

    summary = {
        "total_picks": len(picks),
        "active": len([p for p in picks if p["status"] == "active"]),
        "closed": len([p for p in picks if p["status"] == "closed"]),
        "wins": 0,
        "losses": 0,
        "total_return_pct": 0,
        "by_confidence": {"low": [], "medium": [], "high": []},
        "by_timeframe": {},
    }

    for pick in picks:
        if pick["status"] == "closed" and pick.get("performance_pct") is not None:
            if pick["performance_pct"] > 0:
                summary["wins"] += 1
            else:
                summary["losses"] += 1
            summary["total_return_pct"] += pick["performance_pct"]

        # Group by confidence
        conf = pick.get("confidence", "medium")
        if conf in summary["by_confidence"]:
            summary["by_confidence"][conf].append(pick)

    if summary["closed"] > 0:
        summary["win_rate"] = summary["wins"] / summary["closed"] * 100
        summary["avg_return"] = summary["total_return_pct"] / summary["closed"]
    else:
        summary["win_rate"] = 0
        summary["avg_return"] = 0

    return summary


def add_journal_entry(content: str, tags: list[str] = None) -> dict:
    """
    Add a learning journal entry.

    Args:
        content: What you learned or observed
        tags: Optional tags (e.g., ["NVDA", "valuation", "earnings"])

    Returns:
        The created entry
    """
    ensure_data_files()
    with open(JOURNAL_FILE) as f:
        data = json.load(f)

    entry = {
        "id": len(data["entries"]) + 1,
        "content": content,
        "tags": tags or [],
        "created_at": datetime.now().isoformat(),
    }

    data["entries"].append(entry)

    with open(JOURNAL_FILE, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"✅ Journal entry added")
    return entry


def respond_to_questions(responses: list[dict]) -> dict:
    """
    Log responses to daily learning questions.

    Args:
        responses: List of dicts with question and answer

    Returns:
        The created response record
    """
    ensure_data_files()
    with open(RESPONSES_FILE) as f:
        data = json.load(f)

    record = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "responses": responses,
        "created_at": datetime.now().isoformat(),
    }

    data["responses"].append(record)

    with open(RESPONSES_FILE, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"✅ Responses logged for {record['date']}")
    return record


def interactive_respond():
    """Interactive mode to respond to daily questions."""
    print("\n📝 Daily Question Response Logger")
    print("=" * 40)
    print("Enter your responses to today's questions.")
    print("(Type 'done' when finished, 'skip' to skip a question)\n")

    responses = []
    q_num = 1

    while True:
        question = input(f"Q{q_num} - Paste the question (or 'done'): ").strip()
        if question.lower() == 'done':
            break

        print(f"Your answer for Q{q_num}:")
        answer_lines = []
        while True:
            line = input()
            if line.strip() == '':
                break
            answer_lines.append(line)

        if answer_lines:
            responses.append({
                "question": question,
                "answer": "\n".join(answer_lines),
            })

        q_num += 1

    if responses:
        respond_to_questions(responses)
    else:
        print("No responses recorded.")


def print_picks_table(picks: list[dict]):
    """Print picks in a nice table format."""
    if not picks:
        print("No picks found.")
        return

    print("\n" + "=" * 80)
    print(f"{'ID':<4} {'Symbol':<8} {'Action':<6} {'Conf':<8} {'Status':<8} {'Thesis':<40}")
    print("-" * 80)

    for p in picks:
        thesis_short = p.get('thesis', '')[:37] + "..." if len(p.get('thesis', '')) > 40 else p.get('thesis', '')
        print(f"{p['id']:<4} {p['symbol']:<8} {p['action']:<6} {p.get('confidence', 'med'):<8} {p['status']:<8} {thesis_short}")

    print("=" * 80)


def print_performance():
    """Print performance summary."""
    summary = get_performance_summary()

    print("\n📊 Performance Summary")
    print("=" * 40)
    print(f"Total picks: {summary['total_picks']}")
    print(f"Active: {summary['active']}")
    print(f"Closed: {summary['closed']}")

    if summary['closed'] > 0:
        print(f"\nWins: {summary['wins']} | Losses: {summary['losses']}")
        print(f"Win Rate: {summary['win_rate']:.1f}%")
        print(f"Avg Return: {summary['avg_return']:+.1f}%")

    print("\nBy Confidence Level:")
    for conf, picks in summary['by_confidence'].items():
        print(f"  {conf.title()}: {len(picks)} picks")


def main():
    parser = argparse.ArgumentParser(
        description="Track your AI/tech stock picks and learn from them"
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Add pick
    add_parser = subparsers.add_parser("add", help="Add a new pick")
    add_parser.add_argument("symbol", help="Stock ticker symbol")
    add_parser.add_argument("action", choices=["buy", "sell", "hold", "watch"])
    add_parser.add_argument("thesis", help="Your investment thesis")
    add_parser.add_argument("--timeframe", "-t", default="unspecified", help="Expected timeframe")
    add_parser.add_argument("--price", "-p", type=float, help="Entry price")
    add_parser.add_argument("--confidence", "-c", choices=["low", "medium", "high"], default="medium")
    add_parser.add_argument("--catalyst", help="Key catalyst to watch")

    # List picks
    list_parser = subparsers.add_parser("list", help="List picks")
    list_parser.add_argument("--status", "-s", default="active", choices=["active", "closed", "all"])

    # Close pick
    close_parser = subparsers.add_parser("close", help="Close a pick")
    close_parser.add_argument("pick_id", type=int, help="Pick ID to close")
    close_parser.add_argument("exit_price", type=float, help="Exit price")
    close_parser.add_argument("reason", help="Reason for closing")

    # Performance
    subparsers.add_parser("performance", help="Show performance summary")

    # Respond to questions
    subparsers.add_parser("respond", help="Respond to daily questions")

    # Journal
    journal_parser = subparsers.add_parser("journal", help="Add a journal entry")
    journal_parser.add_argument("content", help="What you learned")
    journal_parser.add_argument("--tags", "-t", nargs="+", help="Tags for the entry")

    args = parser.parse_args()

    if args.command == "add":
        add_pick(
            args.symbol,
            args.action,
            args.thesis,
            args.timeframe,
            args.price,
            args.confidence,
            args.catalyst or "",
        )
    elif args.command == "list":
        picks = list_picks(args.status)
        print_picks_table(picks)
    elif args.command == "close":
        close_pick(args.pick_id, args.exit_price, args.reason)
    elif args.command == "performance":
        print_performance()
    elif args.command == "respond":
        interactive_respond()
    elif args.command == "journal":
        add_journal_entry(args.content, args.tags)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
