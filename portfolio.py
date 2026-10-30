"""Small, independently testable portfolio calculations. No network or UI."""
import re
import numpy as np
import pandas as pd


def parse_tickers(text):
    tickers = [part.strip().upper() for part in text.split(",") if part.strip()]
    if not 3 <= len(tickers) <= 10:
        raise ValueError("Enter between 3 and 10 stock or ETF tickers, separated by commas.")
    if len(set(tickers)) != len(tickers):
        raise ValueError("Each ticker must appear only once.")
    if any(not re.fullmatch(r"[A-Z][A-Z0-9.\-]{0,14}", t) for t in tickers):
        raise ValueError("Use ticker symbols such as AAPL, MSFT, SPY, or BRK-B.")
    return tickers


def normalize_weights(values):
    weights = np.asarray(values, dtype=float)
    if weights.ndim != 1 or not np.isfinite(weights).all() or (weights < 0).any():
        raise ValueError("Weights must be finite, nonnegative numbers.")
    if weights.sum() <= 0:
        raise ValueError("Give at least one holding a weight greater than zero.")
    return weights / weights.sum()


def align_prices(prices, tickers, benchmark="SPY"):
    symbols = list(dict.fromkeys([*tickers, benchmark]))
    missing = [t for t in symbols if t not in prices or prices[t].dropna().empty]
    if missing:
        raise ValueError("No price history returned for: " + ", ".join(missing) + ". Check the ticker or try again later.")
    frame = prices[symbols].copy().sort_index()
    frame = frame[~frame.index.duplicated(keep="last")]
    frame = frame.apply(pd.to_numeric, errors="coerce")
    frame = frame.where(np.isfinite(frame) & (frame > 0))
    original_rows = len(frame)
    frame = frame.dropna(how="any")
    if len(frame) < 3:
        raise ValueError("Not enough overlapping price history. Try different tickers or a longer period.")
    return frame, original_rows - len(frame)


def buy_and_hold(prices, tickers, weights):
    weights = normalize_weights(weights)
    if len(weights) != len(tickers):
        raise ValueError("Provide one starting weight per holding.")
    growth = prices[tickers].div(prices[tickers].iloc[0])
    portfolio = growth.mul(weights, axis=1).sum(axis=1)
    portfolio.name = "Portfolio"
    return growth, portfolio


def risk_metrics(values, annual_risk_free=0.0):
    """Daily observation convention: 252 periods/year, sample standard deviation."""
    values = pd.Series(values, dtype=float)
    if len(values) < 3 or not np.isfinite(values).all() or (values <= 0).any():
        raise ValueError("At least three valid positive portfolio values are required.")
    if not np.isfinite(annual_risk_free) or annual_risk_free <= -1:
        raise ValueError("The annual risk-free rate must be greater than -100%.")
    returns = values.pct_change(fill_method=None).dropna()
    daily_std = returns.std(ddof=1)
    daily_rf = (1 + annual_risk_free) ** (1 / 252) - 1
    return {
        "Total return": values.iloc[-1] / values.iloc[0] - 1,
        "Annualized volatility": daily_std * np.sqrt(252),
        "Sharpe ratio": (returns.mean() - daily_rf) / daily_std * np.sqrt(252)
                        if daily_std > 1e-12 else float("nan"),
        "Maximum drawdown": (values / values.cummax() - 1).min(),
    }
