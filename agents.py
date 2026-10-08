from dataclasses import dataclass
import numpy as np
import pandas as pd


@dataclass
class Signal:
    agent: str
    action: str       # BUY / SELL / HOLD
    confidence: float
    reason: str


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def atr(df: pd.DataFrame, n: int = 14) -> float:
    pc = df["close"].shift()
    tr = pd.concat([df["high"] - df["low"], (df["high"] - pc).abs(),
                    (df["low"] - pc).abs()], axis=1).max(axis=1)
    return float(tr.ewm(alpha=1 / n, adjust=False).mean().iloc[-1])


class DataAgent:
    def fetch(self, symbol: str) -> pd.DataFrame:
        import yfinance as yf
        df = yf.download(symbol, period="1y", interval="1d",
                         auto_adjust=True, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.rename(columns=str.lower).dropna()
        if len(df) < 60:
            raise ValueError(f"not enough data for {symbol}")
        return df


class TechnicalAgent:
    name = "technical"

    def run(self, df):
        r = float(rsi(df["close"]).iloc[-1])
        if r < 30:
            return Signal(self.name, "BUY", 0.7, f"RSI {r:.0f} oversold")
        if r > 70:
            return Signal(self.name, "SELL", 0.7, f"RSI {r:.0f} overbought")
        return Signal(self.name, "HOLD", 0.5, f"RSI {r:.0f} neutral")


class TrendAgent:
    name = "trend"

    def run(self, df):
        c = df["close"]
        s20, s50 = c.rolling(20).mean().iloc[-1], c.rolling(50).mean().iloc[-1]
        if s20 > s50 and c.iloc[-1] > s50:
            return Signal(self.name, "BUY", 0.6, "SMA20 > SMA50, price above SMA50")
        if s20 < s50 and c.iloc[-1] < s50:
            return Signal(self.name, "SELL", 0.6, "SMA20 < SMA50, price below SMA50")
        return Signal(self.name, "HOLD", 0.4, "trend mixed")


class BreakoutAgent:
    name = "breakout"

    def run(self, df):
        prior = df.iloc[:-1]
        if df["close"].iloc[-1] > prior["high"].tail(20).max():
            return Signal(self.name, "BUY", 0.65, "close above 20-day high")
        if df["close"].iloc[-1] < prior["low"].tail(20).min():
            return Signal(self.name, "SELL", 0.65, "close below 20-day low")
        return Signal(self.name, "HOLD", 0.3, "inside 20-day range")


def combine(signals, threshold):
    """Weighted vote -> (action, score)."""
    val = {"BUY": 1, "SELL": -1, "HOLD": 0}
    score = sum(val[s.action] * s.confidence for s in signals) / len(signals)
    if score >= threshold:
        return "BUY", score
    if score <= -threshold:
        return "SELL", score
    return "HOLD", score


class RiskAgent:
    """Plain code, no ML/LLM. The only agent allowed to approve entries."""

    def __init__(self, cfg):
        self.cfg = cfg

    def approve_buy(self, df, equity, cash, n_open, day_return):
        c = self.cfg
        if c.HALT:
            return None, "kill switch on"
        if day_return < -c.DAILY_LOSS_LIMIT:
            return None, "daily loss limit hit"
        if n_open >= c.MAX_OPEN_POSITIONS:
            return None, "max positions reached"
        price, a = float(df["close"].iloc[-1]), atr(df)
        stop, target = price - c.ATR_STOP_MULT * a, price + c.ATR_TARGET_MULT * a
        per_share_risk = price - stop
        if per_share_risk <= 0:
            return None, "bad stop"
        qty = int(min(c.RISK_PER_TRADE * equity / per_share_risk,
                      c.MAX_POSITION_PCT * equity / price,
                      cash / (price * (1 + c.COST_PCT))))
        if qty < 1:
            return None, "size < 1 share"
        return {"qty": qty, "stop": stop, "target": target}, "ok"
