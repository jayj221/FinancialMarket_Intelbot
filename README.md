# AI Market Intelligence

A daily AI-powered market signal report that runs autonomously via GitHub Actions.

Every weekday at 2PM UTC, the pipeline:
1. Fetches live stock and crypto prices via **Finnhub API**
2. Pulls recent financial news per asset
3. Runs **VADER sentiment analysis** on headlines
4. Generates a daily markdown report with composite AI signals
5. Commits the report — keeping the contribution graph active with real work

## Reports

Daily reports are saved to the [`reports/`](./reports/) directory.

Example output:

| Asset | Price    | Day Δ  | Sentiment | AI Signal  |
|-------|----------|--------|-----------|------------|
| AAPL  | $213.42  | +1.2%  | +0.34     | Bullish 📈 |
| TSLA  | $248.11  | -2.1%  | -0.18     | Bearish 📉 |
| NVDA  | $875.00  | +0.8%  | +0.51     | Bullish 📈 |
| BTC   | $83,400  | +3.4%  | +0.62     | Bullish 📈 |

## Setup

1. Get a free API key from [finnhub.io](https://finnhub.io) (no credit card required)
2. Add it to your repo: **Settings → Secrets → Actions → New secret** → `FINNHUB_API_KEY`
3. Push this repo to GitHub
4. Go to **Actions → Daily Market Intelligence → Run workflow** to test

After that, it runs automatically every weekday.

## Stack

- **Data**: [Finnhub API](https://finnhub.io) — prices, news, company data
- **AI/NLP**: [VADER Sentiment](https://github.com/cjhutto/vaderSentiment) — financial text scoring
- **Automation**: GitHub Actions cron schedule
- **Language**: Python 3.11

## Local Development

```bash
pip install -r requirements.txt
python -c "import nltk; nltk.download('vader_lexicon')"
export FINNHUB_API_KEY=your_key_here
PYTHONPATH=src python src/main.py
```
