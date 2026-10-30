"""Portfolio state changes and response assembly, independent of the web server."""
import math
import random
import re
from datetime import date
import numpy as np
from market_data import get_prices
from portfolio import align_prices, buy_and_hold, risk_metrics

UNIVERSE = dict(zip(
    "AAPL MSFT NVDA AMZN GOOGL META JPM V JNJ UNH PG KO PEP WMT COST XOM CVX CAT HD DIS NFLX ADBE CRM CSCO INTC AMD TXN MCD NKE IBM".split(),
    ["Apple", "Microsoft", "NVIDIA", "Amazon", "Alphabet", "Meta Platforms", "JPMorgan Chase", "Visa",
     "Johnson & Johnson", "UnitedHealth", "Procter & Gamble", "Coca-Cola", "PepsiCo", "Walmart",
     "Costco", "Exxon Mobil", "Chevron", "Caterpillar", "Home Depot", "Walt Disney", "Netflix",
     "Adobe", "Salesforce", "Cisco", "Intel", "AMD", "Texas Instruments", "McDonald's", "Nike", "IBM"]))


def distribute(total, weights):
    """Largest-remainder apportionment in basis points; displayed weights sum exactly to 100%."""
    if not weights:
        return []
    w = np.array(weights, dtype=float)
    if not np.isfinite(w).all() or (w < 0).any():
        raise ValueError("Weights must be nonnegative finite numbers.")
    if w.sum() == 0:
        w[:] = 1
    raw = w / w.sum() * total
    result = np.floor(raw).astype(int)
    for i in np.argsort(-(raw-result), kind="stable")[:total-int(result.sum())]:
        result[i] += 1
    return result.tolist()


def edit_weight(weights, index, target):
    if not isinstance(index, int) or not 0 <= index < len(weights):
        raise ValueError("Choose an existing holding.")
    if not isinstance(target, (int, float)) or not math.isfinite(target) or not 0 <= target <= 100:
        raise ValueError("Enter a percentage between 0 and 100.")
    if len(weights) == 1:
        if target != 100:
            raise ValueError("A one-stock portfolio must have a 100% allocation. Add another stock first.")
        return [10000]
    bp = int(round(target * 100))
    remainder = distribute(10000-bp, [w for i,w in enumerate(weights) if i != index])
    remainder.insert(index, bp)
    return remainder


def validate_holding(item):
    if not isinstance(item, dict):
        raise ValueError("Invalid holding.")
    symbol = str(item.get("symbol", "")).strip().upper()
    if not re.fullmatch(r"[A-Z][A-Z0-9-]{0,14}", symbol):
        raise ValueError("Choose a supported US stock or ETF from search.")
    return {"symbol": symbol, "name": str(item.get("name", symbol))[:120]}


def analyze(payload):
    if not isinstance(payload, dict):
        raise ValueError("Invalid portfolio request.")
    holdings = [validate_holding(h) for h in payload.get("holdings", [])]
    if not 1 <= len(holdings) <= 30 or len({h["symbol"] for h in holdings}) != len(holdings):
        raise ValueError("Choose 1–30 different stocks or ETFs.")
    weights = list(payload.get("weights", []))
    if len(weights) != len(holdings) or any(type(w) is not int or w < 0 for w in weights) or sum(weights) != 10000:
        raise ValueError("Portfolio allocations must total exactly 100%.")
    period = payload.get("period", "5y")
    if period not in {"1y", "2y", "5y", "custom"}:
        raise ValueError("Choose a preset history or a custom date range.")
    start_date = end_date = None
    if period == "custom":
        start_date, end_date = payload.get("start_date"), payload.get("end_date")
        try:
            if any(not isinstance(d,str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}",d)
                   for d in (start_date,end_date)):
                raise ValueError
            start, end = date.fromisoformat(start_date), date.fromisoformat(end_date)
        except (ValueError,TypeError):
            raise ValueError("Enter valid start and end dates (YYYY-MM-DD).") from None
        if start < date(1900,1,1) or start >= end:
            raise ValueError("Choose a start date from 1900 onward that is before the end date.")
        if end > date.today():
            raise ValueError("The end date cannot be in the future.")
    rf = payload.get("risk_free", 0)
    if not isinstance(rf, (int,float)) or not math.isfinite(rf) or not 0 <= rf <= .20:
        raise ValueError("The risk-free assumption must be between 0% and 20%.")
    action = payload.get("action") or {}
    kind = action.get("type")
    if kind == "add":
        new = validate_holding(action.get("holding"))
        if new["symbol"] in {h["symbol"] for h in holdings}:
            raise ValueError(f"{new['symbol']} is already in your portfolio.")
        if len(holdings) >= 30:
            raise ValueError("The portfolio already has 30 holdings. Remove one before adding another.")
        target = int(round(10000/(len(holdings)+1)))
        weights = distribute(10000-target, weights) + [target]
        holdings.append(new)
    elif kind == "remove":
        index = action.get("index")
        if not isinstance(index,int) or not 0 <= index < len(holdings) or len(holdings) == 1:
            raise ValueError("Keep at least one holding in the portfolio.")
        holdings.pop(index)
        weights.pop(index)
        weights = distribute(10000, weights)
    elif kind == "edit":
        weights = edit_weight(weights, action.get("index"), action.get("percent"))
    elif kind == "weights":
        proposed = action.get("weights", [])
        if (not isinstance(proposed,list) or len(proposed) != len(holdings)
                or any(type(w) is not int or w < 0 for w in proposed) or sum(proposed) != 10000):
            raise ValueError("Starting allocations must total exactly 100% before applying.")
        weights = proposed
    elif kind == "equal":
        weights = distribute(10000, [1]*len(holdings))
    elif kind == "random":
        count = action.get("count")
        if type(count) is not int or not 1 <= count <= 30:
            raise ValueError("Choose 1–30 stocks for a random mix.")
        holdings = [{"symbol":s,"name":UNIVERSE[s]} for s in random.sample(list(UNIVERSE),count)]
        weights = distribute(10000,[1]*count)
    elif kind not in {None, "refresh"}:
        raise ValueError("Unknown portfolio action.")
    tickers = [h["symbol"] for h in holdings]
    raw, meta = get_prices(tickers, period, refresh=kind=="refresh",start_date=start_date,end_date=end_date)
    if period == "custom":
        raw = raw.loc[start_date:end_date]
    prices, dropped = align_prices(raw,tickers)
    growth, portfolio = buy_and_hold(prices,tickers,np.array(weights)/10000)
    benchmark = prices["SPY"]/prices["SPY"].iloc[0]
    active = [s for s,w in zip(tickers,weights) if w > 0]
    correlations = growth[active].pct_change(fill_method=None).dropna().corr().to_numpy()
    upper = correlations[np.triu_indices(len(active),1)]
    valid = upper[np.isfinite(upper)]
    correlation = float(valid.mean()) if len(valid) else None
    clean = lambda metrics: {k:float(v) if np.isfinite(v) else None for k,v in metrics.items()}
    return {"holdings":holdings,"weights":weights,"period":period,"risk_free":rf,
            "start_date":start_date,"end_date":end_date,
            "dates":prices.index.strftime("%Y-%m-%d").tolist(),
            "series":{t:growth[t].tolist() for t in tickers},"portfolio":portfolio.tolist(),
            "benchmark":benchmark.tolist(),"metrics":clean(risk_metrics(portfolio,rf)),
            "benchmark_metrics":clean(risk_metrics(benchmark,rf)),"correlation":correlation,
            "ending_weights":(growth.iloc[-1].to_numpy()*np.array(weights)/10000/portfolio.iloc[-1]).tolist(),
            "dropped":dropped,"metadata":meta}
