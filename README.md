# Market_Agents

Multi-agent **paper-trading** system for NSE stocks. No paid models or APIs.
Simulated money only. Not investment advice.

## Agents
| Agent | Job |
|---|---|
| DataAgent | Daily OHLCV via `yfinance` |
| TechnicalAgent | RSI oversold / overbought |
| TrendAgent | SMA20 vs SMA50 |
| BreakoutAgent | 20-day high / low breakout |
| Orchestrator (`combine`) | Weighted vote of analyst signals |
| RiskAgent | Hard rules: ATR stop/target, 1% risk sizing, position caps, daily loss limit, kill switch |
| PaperBroker | Simulated fills with 0.1% cost per side, JSON state + CSV trade log |

## Run locally
```
pip install -r requirements.txt
python main.py --demo   # synthetic data, nothing saved
python main.py          # real data, saves to data/
```

## Run on GitHub Actions (works from your phone)
1. Push this repo. Actions runs `main.py` every weekday at 16:15 IST and commits `data/`.
2. Optional alerts: create a Telegram bot with @BotFather, then add repo secrets
   `TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID`.
3. Kill switch: add repo variable `HALT_TRADING=1` to stop new entries.
4. Check `data/trades.csv` and `data/portfolio.json` in the GitHub mobile app.

## Known simplifications
- Signals use the day's close and fill at that close (real trading would fill next open).
- Daily bars only, so stop and target are checked against the day's low/high.
- Evaluate for months and compare against buy-and-hold Nifty before trusting anything.
