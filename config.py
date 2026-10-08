import os

WATCHLIST = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
             "SBIN.NS", "ITC.NS", "LT.NS"]

START_CAPITAL = 100_000        # paper money (INR)
RISK_PER_TRADE = 0.01          # risk 1% of equity per trade (distance to stop)
MAX_POSITION_PCT = 0.20        # no position bigger than 20% of equity
MAX_OPEN_POSITIONS = 5
DAILY_LOSS_LIMIT = 0.02        # no new buys if equity fell >2% since last run
COST_PCT = 0.001               # 0.1% per side: brokerage + STT + slippage (rough)
ATR_STOP_MULT = 2.0
ATR_TARGET_MULT = 3.0
SIGNAL_THRESHOLD = 0.25        # |combined score| needed to act

# Kill switch: set env HALT_TRADING=1 to stop all new entries
HALT = os.getenv("HALT_TRADING", "0") == "1"
STATE_FILE = "data/portfolio.json"
TRADES_FILE = "data/trades.csv"
