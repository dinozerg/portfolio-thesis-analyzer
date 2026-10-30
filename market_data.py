"""Yahoo Finance API adapter with a clearly identified local outage fallback."""
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import hashlib
import json
import time
import threading
import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / ".cache"
_memory = {}
_search_cache = {}
_lock = threading.RLock()


def search_stocks(query):
    """Live company/ticker lookup; restrict results to supported US equity/ETF listings."""
    query = str(query).strip()
    if not 1 <= len(query) <= 80:
        raise ValueError("Enter a company name or ticker (up to 80 characters).")
    key = query.casefold()
    with _lock:
        cached = _search_cache.get(key)
        if cached and time.monotonic() - cached[0] < 3600:
            return cached[1]
    try:
        quotes = yf.Search(query, max_results=15, news_count=0, lists_count=0,
                           recommended=0, include_cb=False, timeout=8).quotes
    except Exception as exc:
        raise ValueError("Stock search is unavailable. Please try again in a moment.") from exc
    exchanges = {"NYQ", "NMS", "NGM", "NCM", "ASE", "PCX", "BTS", "NAS", "NYSE", "ARCA"}
    results, seen = [], set()
    for q in quotes:
        symbol = q.get("symbol", "")
        if (q.get("quoteType") not in {"EQUITY", "ETF"} or q.get("exchange") not in exchanges
                or symbol in seen):
            continue
        seen.add(symbol)
        results.append({"symbol": symbol, "name": q.get("longname") or q.get("shortname") or symbol,
                        "exchange": q.get("exchDisp") or q.get("exchange"), "type": q["quoteType"]})
    with _lock:
        _search_cache[key] = (time.monotonic(), results[:8])
    return results[:8]


def get_prices(tickers, period, refresh=False, start_date=None, end_date=None):
    key = (tuple(sorted(set(tickers))), period, start_date, end_date)
    # Serialize downloads: yfinance maintains internal shared caches.
    with _lock:
        cached = _memory.get(key)
        if not refresh and cached and time.monotonic() - cached[0] < 3600:
            return cached[1].copy(), dict(cached[2])
        prices, metadata = fetch_prices(tickers, period, start_date, end_date)
        if not metadata["cached_fallback"]:
            _memory[key] = (time.monotonic(), prices.copy(), dict(metadata))
        return prices, metadata


def fetch_prices(tickers, period, start_date=None, end_date=None):
    CACHE.mkdir(exist_ok=True)
    yf.set_tz_cache_location(str(CACHE / "yfinance"))
    symbols = sorted(set([*tickers, "SPY"]))
    window = [period,start_date,end_date] if period == "custom" else period
    key = hashlib.sha256(json.dumps([symbols, window]).encode()).hexdigest()[:20]
    csv_path = CACHE / f"{key}.csv"
    meta_path = CACHE / f"{key}.json"
    try:
        # The UI's end date is inclusive; yfinance's end parameter is exclusive.
        window_args = ({"start":start_date,"end":(date.fromisoformat(end_date)+timedelta(days=1)).isoformat()}
                       if period == "custom" else {"period":period})
        data = yf.download(symbols, **window_args, interval="1d", auto_adjust=True,
                           progress=False, threads=False, timeout=12)
        if data is None or data.empty:
            raise ValueError("The provider returned no prices.")
        if isinstance(data.columns, pd.MultiIndex):
            prices = data["Close"].copy()
        else:
            prices = data[["Close"]].rename(columns={"Close": symbols[0]})
        prices.index = pd.to_datetime(prices.index).tz_localize(None)
        if period == "custom":
            prices = prices.loc[start_date:end_date]
        # Cache only complete symbol responses; never silently drop a failed ticker.
        missing = [t for t in symbols if t not in prices or prices[t].dropna().empty]
        if missing:
            raise ValueError("No data for " + ", ".join(missing))
        metadata = {"retrieved_utc": datetime.now(timezone.utc).isoformat(),
                    "source": "Yahoo Finance via yfinance (adjusted daily close)",
                    "cached_fallback": False}
        prices.to_csv(csv_path, index_label="Date")
        meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        return prices, metadata
    except Exception as exc:
        if csv_path.exists() and meta_path.exists():
            prices = pd.read_csv(csv_path, index_col="Date", parse_dates=True)
            metadata = json.loads(meta_path.read_text(encoding="utf-8"))
            metadata["cached_fallback"] = True
            return prices, metadata
        raise ValueError(
            "Could not load historical prices. Check your connection and tickers, or try a wider date range, "
            "then press Refresh prices. Yahoo Finance may also temporarily limit requests. "
            "No simulated data has been substituted."
        ) from exc
