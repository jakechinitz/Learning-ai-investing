"""
Telegram Bot for AI Investing Daily Reports
Sends daily briefings and logs your responses automatically.

Setup:
1. Message @BotFather on Telegram
2. Create a new bot with /newbot
3. Copy the bot token
4. Add to .env: TELEGRAM_BOT_TOKEN=your_token
5. Start a chat with your bot and send /start
6. Run: python -m src.delivery.telegram_bot --get-chat-id
7. Add to .env: TELEGRAM_CHAT_ID=your_chat_id
"""

import os
import json
import asyncio
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from telegram import Update, Bot
    from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    print("Install python-telegram-bot: pip install python-telegram-bot")

# Load environment
from dotenv import load_dotenv
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
PICKS_FILE = DATA_DIR / "picks.json"
RESPONSES_FILE = DATA_DIR / "question_responses.json"


def extract_stock_picks(message: str) -> list[dict]:
    """
    Parse natural language message to extract stock picks.

    Examples it handles:
    - "I'm bullish on NVDA, think it goes to 200"
    - "Buying AMD here, AI GPUs are undervalued"
    - "Sell INTC - foundry strategy isn't working"
    - "AVGO looks interesting for custom AI chips"
    """
    picks = []

    # Common stock symbols (uppercase 1-5 letters)
    # Load from config for accuracy
    try:
        import yaml
        config_path = Path(__file__).parent.parent.parent / "config" / "sources.yaml"
        with open(config_path) as f:
            config = yaml.safe_load(f)

        all_symbols = set()
        for category in config.get('watchlist', {}).values():
            if isinstance(category, list):
                for stock in category:
                    all_symbols.add(stock.get('symbol', ''))
    except:
        all_symbols = {'NVDA', 'AMD', 'AVGO', 'MSFT', 'GOOGL', 'META', 'AMZN', 'AAPL'}

    # Find mentioned symbols
    words = re.findall(r'\b[A-Z]{1,5}\b', message.upper())
    mentioned_symbols = [w for w in words if w in all_symbols]

    # Determine sentiment for each
    message_lower = message.lower()

    buy_signals = ['buy', 'bullish', 'long', 'adding', 'accumulating', 'like', 'love', 'undervalued']
    sell_signals = ['sell', 'bearish', 'short', 'reducing', 'overvalued', 'avoid', 'dump']
    watch_signals = ['watching', 'interesting', 'monitor', 'wait', 'considering']

    for symbol in mentioned_symbols:
        action = 'watch'  # default

        if any(sig in message_lower for sig in buy_signals):
            action = 'buy'
        elif any(sig in message_lower for sig in sell_signals):
            action = 'sell'
        elif any(sig in message_lower for sig in watch_signals):
            action = 'watch'

        picks.append({
            'symbol': symbol,
            'action': action,
            'raw_message': message,
            'extracted_at': datetime.now().isoformat(),
        })

    return picks


def save_pick(pick: dict):
    """Save an extracted pick to the picks file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if PICKS_FILE.exists():
        with open(PICKS_FILE) as f:
            data = json.load(f)
    else:
        data = {"picks": [], "version": "1.0"}

    pick_record = {
        "id": len(data["picks"]) + 1,
        "symbol": pick['symbol'],
        "action": pick['action'],
        "thesis": pick.get('raw_message', '')[:200],
        "timeframe": "unspecified",
        "confidence": "medium",
        "created_at": datetime.now().isoformat(),
        "status": "active",
        "source": "telegram",
    }

    data["picks"].append(pick_record)

    with open(PICKS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

    return pick_record


def save_response(message: str):
    """Save a message as a question response."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if RESPONSES_FILE.exists():
        with open(RESPONSES_FILE) as f:
            data = json.load(f)
    else:
        data = {"responses": []}

    record = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "message": message,
        "created_at": datetime.now().isoformat(),
        "source": "telegram",
    }

    data["responses"].append(record)

    with open(RESPONSES_FILE, 'w') as f:
        json.dump(data, f, indent=2)


async def send_daily_report(bot: Bot, chat_id: str):
    """Send the daily report via Telegram."""
    from src.report_generator import generate_daily_report

    report = generate_daily_report()

    # Telegram has a 4096 character limit per message
    # Split into chunks
    chunks = []
    current_chunk = ""

    for line in report.split('\n'):
        if len(current_chunk) + len(line) + 1 > 4000:
            chunks.append(current_chunk)
            current_chunk = line
        else:
            current_chunk += '\n' + line if current_chunk else line

    if current_chunk:
        chunks.append(current_chunk)

    for i, chunk in enumerate(chunks):
        await bot.send_message(
            chat_id=chat_id,
            text=chunk,
            parse_mode='Markdown',
            disable_web_page_preview=True
        )
        if i < len(chunks) - 1:
            await asyncio.sleep(0.5)  # Rate limiting

    # Send prompt for response
    await bot.send_message(
        chat_id=chat_id,
        text="💬 *Reply with your thoughts!*\n\nI'll automatically log your responses and extract any stock picks you mention.\n\nExample: \"Bullish on NVDA, datacenter numbers were insane. Watching AMD for MI300 traction.\"",
        parse_mode='Markdown'
    )


# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    chat_id = update.effective_chat.id
    await update.message.reply_text(
        f"👋 Welcome to AI Investing Daily!\n\n"
        f"Your Chat ID: `{chat_id}`\n\n"
        f"Add this to your .env file:\n"
        f"`TELEGRAM_CHAT_ID={chat_id}`\n\n"
        f"Commands:\n"
        f"/report - Get today's report\n"
        f"/picks - View your picks\n"
        f"/performance - See your stats\n\n"
        f"Or just reply with your thoughts and I'll log them!",
        parse_mode='Markdown'
    )


async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /report command."""
    await update.message.reply_text("📊 Generating your daily report...")
    await send_daily_report(context.bot, update.effective_chat.id)


async def picks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /picks command."""
    if PICKS_FILE.exists():
        with open(PICKS_FILE) as f:
            data = json.load(f)

        active_picks = [p for p in data['picks'] if p.get('status') == 'active']

        if active_picks:
            msg = "📈 *Your Active Picks:*\n\n"
            for p in active_picks[-10:]:  # Last 10
                msg += f"• {p['action'].upper()} *{p['symbol']}*\n"
                msg += f"  _{p.get('thesis', 'No thesis')[:50]}..._\n\n"
        else:
            msg = "No active picks yet. Reply with your stock ideas!"
    else:
        msg = "No picks recorded yet. Start by sharing your thoughts!"

    await update.message.reply_text(msg, parse_mode='Markdown')


async def performance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /performance command."""
    if PICKS_FILE.exists():
        with open(PICKS_FILE) as f:
            data = json.load(f)

        picks = data['picks']
        active = len([p for p in picks if p.get('status') == 'active'])
        closed = len([p for p in picks if p.get('status') == 'closed'])

        msg = f"📊 *Your Stats:*\n\n"
        msg += f"Total picks: {len(picks)}\n"
        msg += f"Active: {active}\n"
        msg += f"Closed: {closed}\n"

        if RESPONSES_FILE.exists():
            with open(RESPONSES_FILE) as f:
                responses = json.load(f)
            msg += f"\nDaily responses: {len(responses.get('responses', []))}"
    else:
        msg = "No stats yet. Start engaging with daily reports!"

    await update.message.reply_text(msg, parse_mode='Markdown')


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular messages - extract picks and log responses."""
    message = update.message.text

    # Save the full response
    save_response(message)

    # Extract any stock picks
    picks = extract_stock_picks(message)

    if picks:
        saved_picks = []
        for pick in picks:
            saved = save_pick(pick)
            saved_picks.append(saved)

        # Confirm to user
        pick_summary = ', '.join([f"{p['action'].upper()} {p['symbol']}" for p in saved_picks])
        await update.message.reply_text(
            f"✅ Logged your response!\n\n"
            f"📝 Extracted picks: {pick_summary}\n\n"
            f"_These are now tracked in your portfolio._",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "✅ Response logged!\n\n"
            "_Tip: Mention stock symbols (NVDA, AMD, etc.) with buy/sell/watch to track picks._",
            parse_mode='Markdown'
        )


def run_bot():
    """Run the Telegram bot."""
    if not TELEGRAM_AVAILABLE:
        print("Error: python-telegram-bot not installed")
        print("Run: pip install python-telegram-bot")
        return

    if not BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not set in .env")
        print("1. Message @BotFather on Telegram")
        print("2. Create a bot with /newbot")
        print("3. Add token to .env: TELEGRAM_BOT_TOKEN=your_token")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("report", report_command))
    app.add_handler(CommandHandler("picks", picks_command))
    app.add_handler(CommandHandler("performance", performance_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Bot is running! Press Ctrl+C to stop.")
    app.run_polling()


async def send_scheduled_report():
    """Send a one-time scheduled report (for cron/GitHub Actions)."""
    if not BOT_TOKEN or not CHAT_ID:
        print("Error: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID required in .env")
        return

    bot = Bot(token=BOT_TOKEN)
    await send_daily_report(bot, CHAT_ID)
    print("✅ Daily report sent!")


if __name__ == "__main__":
    import sys

    if "--send-report" in sys.argv:
        # One-time send (for cron)
        asyncio.run(send_scheduled_report())
    elif "--get-chat-id" in sys.argv:
        print("Start the bot and send /start to get your chat ID")
        run_bot()
    else:
        # Run interactive bot
        run_bot()
