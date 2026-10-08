import sys
import numpy as np
import pandas as pd
import config
from agents import (DataAgent, TechnicalAgent, TrendAgent, BreakoutAgent,
                    RiskAgent, combine)
from broker import PaperBroker
import notify


def demo_df(seed):
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(0.0005, 0.015, 250)))
    idx = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=250)
    return pd.DataFrame({"open": close, "high": close * 1.01, "low": close * 0.99,
                         "close": close, "volume": 1e6}, index=idx)


def main(demo=False):
    data, risk = DataAgent(), RiskAgent(config)
    analysts = [TechnicalAgent(), TrendAgent(), BreakoutAgent()]
    broker, lines = PaperBroker(config), []

    frames = {}
    for i, sym in enumerate(config.WATCHLIST):
        try:
            frames[sym] = demo_df(i) if demo else data.fetch(sym)
        except Exception as e:
            lines.append(f"skip {sym}: {e}")
    if not frames:
        notify.send("No data fetched, nothing done.")
        return

    date = str(max(df.index[-1] for df in frames.values()).date())
    if broker.s["last_date"] == date and not demo:
        print("Already processed", date)
        return

    prices = {s: float(df["close"].iloc[-1]) for s, df in frames.items()}
    day_return = broker.equity(prices) / broker.s["last_equity"] - 1

    # 1) exits: stop / target hit during the day, else SELL consensus
    for sym in list(broker.s["positions"]):
        if sym not in frames:
            continue
        df, p = frames[sym], broker.s["positions"][sym]
        low, high = float(df["low"].iloc[-1]), float(df["high"].iloc[-1])
        if low <= p["stop"]:
            pnl = broker.sell(date, sym, p["stop"], "stop-loss")
            lines.append(f"SELL {sym} @ stop {p['stop']:.2f} pnl {pnl:+.0f}")
        elif high >= p["target"]:
            pnl = broker.sell(date, sym, p["target"], "target")
            lines.append(f"SELL {sym} @ target {p['target']:.2f} pnl {pnl:+.0f}")
        else:
            action, score = combine([a.run(df) for a in analysts], config.SIGNAL_THRESHOLD)
            if action == "SELL":
                pnl = broker.sell(date, sym, prices[sym], f"signal {score:+.2f}")
                lines.append(f"SELL {sym} @ {prices[sym]:.2f} pnl {pnl:+.0f}")

    # 2) entries
    for sym, df in frames.items():
        if sym in broker.s["positions"]:
            continue
        sigs = [a.run(df) for a in analysts]
        action, score = combine(sigs, config.SIGNAL_THRESHOLD)
        if action != "BUY":
            continue
        eq = broker.equity(prices)
        plan, why = risk.approve_buy(df, eq, broker.s["cash"],
                                     len(broker.s["positions"]), day_return)
        if plan:
            reason = "; ".join(f"{s.agent}:{s.action}" for s in sigs)
            broker.buy(date, sym, plan["qty"], prices[sym], plan["stop"],
                       plan["target"], reason)
            lines.append(f"BUY {sym} x{plan['qty']} @ {prices[sym]:.2f} "
                         f"(stop {plan['stop']:.2f}, target {plan['target']:.2f})")
        else:
            lines.append(f"no buy {sym}: {why}")

    eq = broker.equity(prices)
    broker.s.update(last_date=date, last_equity=eq)
    broker.s["equity_curve"].append({"date": date, "equity": round(eq, 2)})
    if not demo:
        broker.save()
    ret = (eq / config.START_CAPITAL - 1) * 100
    header = (f"[PAPER] {date} equity Rs{eq:,.0f} ({ret:+.2f}% total), "
              f"{len(broker.s['positions'])} open")
    notify.send("\n".join([header] + (lines or ["no trades today"])))


if __name__ == "__main__":
    main(demo="--demo" in sys.argv)
