# AI Investing Learning System

A personal system for learning AI/tech investing through curated content, daily briefings delivered to your phone, and automatic pick tracking.

## What This Does

1. **Daily Briefings Delivered to You** - Get a push notification every morning with AI investing news
2. **Just Reply** - Respond naturally and your picks are auto-extracted and logged
3. **Track Performance** - See how your picks do over time
4. **Learn by Doing** - Educational questions to build investing intuition

## Quick Start (5 minutes)

### Option 1: Telegram Bot (Recommended)

1. **Create your bot:**
   - Open Telegram, search for `@BotFather`
   - Send `/newbot`, follow prompts, get your token

2. **Configure:**
   ```bash
   cp .env.example .env
   # Edit .env and add your TELEGRAM_BOT_TOKEN
   ```

3. **Get your Chat ID:**
   ```bash
   pip install -r requirements.txt
   python -m src.delivery.telegram_bot --get-chat-id
   # Send /start to your bot, it will reply with your Chat ID
   # Add TELEGRAM_CHAT_ID to .env
   ```

4. **Test it:**
   ```bash
   python -m src.delivery.telegram_bot --send-report
   ```

5. **Enable daily automation:**
   - Go to repo Settings → Secrets → Actions
   - Add `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`
   - Reports will be sent every weekday at 7 AM EST

### Option 2: Email

See `.env.example` for Gmail, Resend, or SendGrid configuration.

## Daily Workflow

### Morning
- Get a Telegram notification with your daily briefing
- Read the curated content (Substacks, podcasts, Twitter insights)
- See educational questions at the bottom

### Respond Naturally
Just reply to the bot with your thoughts:

> "Bullish on NVDA here, datacenter numbers were insane. The AI training demand is real. Also watching AMD to see if MI300 gets traction."

The bot automatically:
- Logs your full response
- Extracts stock picks: `BUY NVDA`, `WATCH AMD`
- Tracks them in your portfolio

### Track Your Progress
Send `/picks` to see your active picks
Send `/performance` to see your stats

## Stock Coverage

### Complete SOXX ETF Holdings (35 stocks)
All semiconductor stocks including:
- **Top 10:** AVGO, AMD, NVDA, MU, INTC, AMAT, QCOM, LRCX, MRVL, ASML
- **Mid-tier:** ADI, TXN, KLAC, NXPI, ON, MPWR, MCHP, ARM, GFS, SWKS
- **Smaller:** ENTG, TER, MKSI, QRVO, WOLF, LSCC, ACLS, AMKR, CRUS, SLAB, ALGM, RMBS, COHR, MTSI, DIOD

### Plus AI/Tech Leaders
- **Mega Cap:** MSFT, GOOGL, AMZN, META, AAPL
- **AI Software:** CRM, NOW, PLTR, SNOW, MDB, DDOG, PANW, CRWD, ZS, NET
- **AI Infrastructure:** SMCI, VRT, DELL, HPE, ANET, CSCO, VST, CEG, EQIX, DLR
- **AI Pure Plays:** PATH, AI, SOUN, UPST, S

See `config/sources.yaml` for complete list with investment theses.

## Content Sources

### Substacks
| Newsletter | Focus |
|------------|-------|
| SemiAnalysis | Semiconductor deep dives, AI infrastructure |
| Stratechery | Tech strategy, platform dynamics |
| Not Boring | Tech trends, company deep dives |
| Fabricated Knowledge | Semiconductor analysis |

### Podcasts
| Podcast | Why Listen |
|---------|-----------|
| All-In | Real-time takes from tech investors |
| Acquired | How great tech companies were built |
| Invest Like the Best | Professional investor frameworks |
| BG2 Pod | Bill Gurley + Brad Gerstner |

### Twitter/X
10 curated accounts for AI investing insights. See `config/sources.yaml`.

## Bot Commands

| Command | What it does |
|---------|--------------|
| `/start` | Get your Chat ID for setup |
| `/report` | Get today's report on-demand |
| `/picks` | View your active picks |
| `/performance` | See your stats |
| (any message) | Logged + picks extracted |

## Learning Frameworks

The system teaches you to think about:

### Valuation
- P/E vs growth rate (PEG ratio)
- EV/Revenue for growth companies
- Free cash flow yield
- Rule of 40 for SaaS

### AI-Specific Questions
- What is the company's right to win in AI?
- Is this pick-and-shovel or direct AI bet?
- How defensible is the AI advantage?
- What's priced in at current valuation?

## File Structure

```
Learning-ai-investing/
├── config/
│   └── sources.yaml         # All sources and 70+ stocks
├── data/
│   ├── picks.json           # Your tracked picks (auto-synced)
│   ├── question_responses.json
│   └── reports/             # Daily report archive
├── src/
│   ├── delivery/
│   │   ├── telegram_bot.py  # Telegram delivery + response parsing
│   │   └── email_sender.py  # Email delivery option
│   ├── fetchers/            # Content fetchers
│   └── report_generator.py  # Builds daily reports
├── .env.example             # Configuration template
└── requirements.txt
```

## Automation

Reports are automatically generated and sent via GitHub Actions:
- Every weekday at 7 AM EST
- Sent to Telegram (or email as fallback)
- Archived in `data/reports/`

To enable:
1. Add secrets to your repo (Settings → Secrets → Actions)
2. Enable GitHub Actions (Settings → Actions → General)

## Philosophy

This system is designed for **active learning**:

1. **Read with purpose** - Reports highlight what matters
2. **Form opinions** - Reply with your thoughts
3. **Track outcomes** - See if you were right
4. **Iterate** - Learn from wins and losses

The goal isn't to be right every time. It's to improve your thinking over time.

---

*Built for learning AI/tech investing the hard way - by doing it.*
