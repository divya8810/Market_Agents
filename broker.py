import csv, json, os
from datetime import datetime


class PaperBroker:
    """Simulated broker. State lives in a JSON file; trades in a CSV."""

    def __init__(self, cfg):
        self.cfg = cfg
        if os.path.exists(cfg.STATE_FILE):
            self.s = json.load(open(cfg.STATE_FILE))
        else:
            self.s = {"cash": cfg.START_CAPITAL, "positions": {},
                      "last_date": None, "last_equity": cfg.START_CAPITAL,
                      "equity_curve": []}

    def equity(self, prices):
        return self.s["cash"] + sum(p["qty"] * prices.get(sym, p["entry"])
                                    for sym, p in self.s["positions"].items())

    def _log(self, date, sym, side, qty, price, reason, pnl=""):
        new = not os.path.exists(self.cfg.TRADES_FILE)
        with open(self.cfg.TRADES_FILE, "a", newline="") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["date", "symbol", "side", "qty", "price", "reason", "pnl"])
            w.writerow([date, sym, side, qty, round(price, 2), reason, pnl])

    def buy(self, date, sym, qty, price, stop, target, reason):
        cost = qty * price * (1 + self.cfg.COST_PCT)
        self.s["cash"] -= cost
        self.s["positions"][sym] = {"qty": qty, "entry": price, "stop": stop,
                                    "target": target}
        self._log(date, sym, "BUY", qty, price, reason)

    def sell(self, date, sym, price, reason):
        p = self.s["positions"].pop(sym)
        proceeds = p["qty"] * price * (1 - self.cfg.COST_PCT)
        self.s["cash"] += proceeds
        pnl = proceeds - p["qty"] * p["entry"]
        self._log(date, sym, "SELL", p["qty"], price, reason, round(pnl, 2))
        return pnl

    def save(self):
        os.makedirs(os.path.dirname(self.cfg.STATE_FILE), exist_ok=True)
        json.dump(self.s, open(self.cfg.STATE_FILE, "w"), indent=2)
