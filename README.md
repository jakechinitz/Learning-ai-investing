# AI Investing Learning System 📈🤖

A personal system for learning AI/tech investing through curated content, daily briefings, and tracked picks.

## What This Does

1. **Aggregates Content** - Pulls from Substacks, podcasts, and curated Twitter
2. **Daily Briefings** - Generates morning reports with stock-specific insights
3. **Educational Questions** - Asks you questions to build investing intuition
4. **Pick Tracking** - Log your picks, track performance, see if you're improving

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Generate your first report
python generate_report.py

# View the report
cat data/reports/report_$(date +%Y-%m-%d).md
```

## Daily Workflow

### Morning (10 min)
```bash
# Generate and read today's report
python generate_report.py
```

Review the briefing:
- 📰 Substack highlights (must-reads flagged with 🔥)
- 🎙️ Recent podcast episodes (stocks mentioned tagged)
- 🐦 Twitter insights (with reasoning why they matter)
- 📝 Learning questions to answer

### Throughout the Day
When you see interesting tweets, save them:
```bash
# Edit data/twitter_highlights.json to add notable tweets
```

### Evening (5 min)
```bash
# Log your thoughts on today's questions
python -m src.pick_tracker respond

# Add any investment ideas you had
python -m src.pick_tracker add NVDA buy "Datacenter growth accelerating" -t 6mo -c high

# Journal learnings
python -m src.pick_tracker journal "ASML's monopoly is more durable than I thought" -t ASML moat
```

## Commands Reference

### Pick Tracker

```bash
# Add a pick
python -m src.pick_tracker add <SYMBOL> <buy|sell|hold|watch> "<thesis>" \
    --timeframe <1mo|3mo|6mo|1yr> \
    --confidence <low|medium|high> \
    --price 150.00 \
    --catalyst "Upcoming earnings"

# Examples
python -m src.pick_tracker add NVDA buy "AI training demand exceeding supply" -t 6mo -c high
python -m src.pick_tracker add AMD watch "Waiting for MI300 traction data" -t 3mo -c medium
python -m src.pick_tracker add SMCI sell "Valuation stretched, competition coming" -t 3mo -c low

# List your picks
python -m src.pick_tracker list           # Active picks
python -m src.pick_tracker list -s all    # All picks
python -m src.pick_tracker list -s closed # Closed picks

# Close a pick (record outcome)
python -m src.pick_tracker close 1 175.50 "Thesis played out, taking profits"

# See your performance
python -m src.pick_tracker performance

# Answer daily questions
python -m src.pick_tracker respond

# Add journal entry
python -m src.pick_tracker journal "Key insight here" -t NVDA semiconductors
```

## Sources Included

### Substacks (Must-Reads 🔥)
| Newsletter | Focus |
|------------|-------|
| SemiAnalysis | Semiconductor deep dives, AI infrastructure |
| Stratechery | Tech strategy, platform dynamics |
| Not Boring | Tech trends, company deep dives |
| Fabricated Knowledge | Semiconductor analysis |

### Podcasts
| Podcast | Why Listen |
|---------|-----------|
| All-In | Real-time takes from successful tech investors |
| Acquired | How great tech companies were built |
| Invest Like the Best | Learn how professional investors think |
| BG2 Pod | Bill Gurley + Brad Gerstner on markets |

### Twitter Accounts
See `config/sources.yaml` for the full list with context on each account.

## Stock Watchlist

The system tracks mentions of key AI/tech stocks:

**Mega Cap:** NVDA, MSFT, GOOGL, AMZN, META, AAPL
**Semiconductors:** AMD, AVGO, TSM, ASML, ARM, MRVL
**AI Software:** CRM, NOW, PLTR, SNOW, MDB, DDOG
**Pure Plays:** SMCI, VRT, DELL, PATH

## Learning Frameworks

The system teaches you to think using these frameworks:

### Valuation
- P/E vs growth rate (PEG ratio)
- EV/Revenue for growth companies
- Free cash flow yield
- Rule of 40 for SaaS

### Competitive Moats
- Network effects
- Switching costs
- Economies of scale
- Intangible assets (brand, IP)
- Cost advantages

### AI-Specific Questions
- What is the company's right to win in AI?
- Is this pick-and-shovel or direct AI bet?
- How defensible is the AI advantage?
- What's priced in at current valuation?
- What could go wrong? (steelman the bear case)

## Automation

### GitHub Actions (Recommended)
The repo includes a workflow that generates reports every weekday at 7 AM EST.

Enable it:
1. Go to repo Settings → Actions → General
2. Enable "Allow all actions"
3. Reports will appear in `data/reports/`

### Local Cron
```bash
# Add to crontab (crontab -e)
0 7 * * 1-5 cd /path/to/Learning-ai-investing && python generate_report.py
```

## Cloud Sync

Your picks are stored in `data/picks.json`. Since it's in the git repo:

```bash
# After making picks, commit them
git add data/
git commit -m "Update picks and responses"
git push
```

For real-time sync, consider:
- Syncing `data/` to Dropbox/iCloud
- Using a simple database (SQLite → Turso or Supabase)

## Customization

### Add Sources
Edit `config/sources.yaml`:

```yaml
substacks:
  - name: "New Newsletter"
    url: "https://example.substack.com"
    rss: "https://example.substack.com/feed"
    focus: "What they cover"
```

### Add Stocks to Watch
```yaml
watchlist:
  my_picks:
    - symbol: "TICKER"
      name: "Company Name"
      thesis: "Why you're watching"
```

## File Structure

```
Learning-ai-investing/
├── config/
│   └── sources.yaml         # Twitter, Substacks, podcasts config
├── data/
│   ├── picks.json           # Your stock picks
│   ├── journal.json         # Learning journal
│   ├── question_responses.json
│   ├── twitter_highlights.json
│   └── reports/             # Daily report archive
├── src/
│   ├── fetchers/            # Content fetchers
│   ├── report_generator.py  # Builds daily reports
│   └── pick_tracker.py      # CLI for tracking picks
├── .github/workflows/       # Automation
├── generate_report.py       # Quick entry point
└── requirements.txt
```

## Philosophy

This system is designed for **active learning**, not passive consumption:

1. **Read with purpose** - Reports highlight what matters for investing
2. **Form opinions** - Forced to answer questions and make picks
3. **Track outcomes** - See if your reasoning was right
4. **Iterate** - Learn from wins and losses

The goal isn't to be right every time. It's to improve your thinking over time.

---

*Built for learning AI/tech investing the hard way - by doing it.*
