import unittest
from unittest.mock import patch
import tempfile
from pathlib import Path
import numpy as np
import pandas as pd
from portfolio import parse_tickers, normalize_weights, align_prices, buy_and_hold, risk_metrics
import market_data


class PortfolioTests(unittest.TestCase):
    def test_risk_metrics_known_returns(self):
        # Returns +10%, -20%, +25%; average 5%, sample variance .0525.
        metrics = risk_metrics([100,110,88,110])
        self.assertAlmostEqual(metrics["Total return"],.1)
        self.assertAlmostEqual(metrics["Annualized volatility"],np.sqrt(.0525*252))
        self.assertAlmostEqual(metrics["Sharpe ratio"],.05/np.sqrt(.0525)*np.sqrt(252))
        self.assertAlmostEqual(metrics["Maximum drawdown"],-.2)

    def test_drawdown_includes_initial_capital_and_zero_volatility(self):
        self.assertAlmostEqual(risk_metrics([100,90,81])["Maximum drawdown"],-.19)
        metrics = risk_metrics([100,100,100])
        self.assertEqual(metrics["Annualized volatility"],0)
        self.assertTrue(np.isnan(metrics["Sharpe ratio"]))
        self.assertEqual(metrics["Maximum drawdown"],0)

    def test_risk_free_rate_changes_only_sharpe(self):
        zero = risk_metrics([100,110,88,110])
        rf = risk_metrics([100,110,88,110],.05)
        self.assertLess(rf["Sharpe ratio"],zero["Sharpe ratio"])
        self.assertEqual(rf["Maximum drawdown"],zero["Maximum drawdown"])

    def setUp(self):
        self.prices = pd.DataFrame({"AAPL":[100,110,121], "MSFT":[100,90,81],
                                    "SPY":[100,100,100]}, index=pd.date_range("2025-01-01", periods=3))

    def test_buy_and_hold_known_example(self):
        # $40 grows to $48.40; $35 falls to $28.35; $25 stays $25.
        growth, portfolio = buy_and_hold(self.prices, list(self.prices), [40,35,25])
        np.testing.assert_allclose(portfolio, [1, 1.005, 1.0175])
        np.testing.assert_allclose(growth.iloc[0], [1,1,1])

    def test_not_daily_rebalanced(self):
        _, result = buy_and_hold(self.prices, list(self.prices), [50,50,0])
        self.assertAlmostEqual(result.iloc[-1], 1.01)  # daily rebalancing would end at 1.00

    def test_weight_validation(self):
        np.testing.assert_allclose(normalize_weights([20,30,50]), [.2,.3,.5])
        np.testing.assert_allclose(normalize_weights([10,10,10]), [1/3]*3)
        for values in ([0,0,0], [-1,2,3], [float("nan"),1,2], [float("inf"),1,2]):
            with self.assertRaises(ValueError): normalize_weights(values)

    def test_missing_prices_never_forward_filled(self):
        self.prices.loc[pd.Timestamp("2025-01-04")] = [np.nan,82,100]
        clean, dropped = align_prices(self.prices, list(self.prices))
        self.assertEqual(len(clean),3)
        self.assertEqual(dropped,1)

    def test_missing_ticker_fails(self):
        with self.assertRaises(ValueError): align_prices(self.prices, ["AAPL","MSFT","INVALID"])

    def test_ticker_validation(self):
        self.assertEqual(parse_tickers(" aapl, msft, brk-b "), ["AAPL","MSFT","BRK-B"])
        for text in ("AAPL,MSFT", "AAPL,AAPL,SPY", "AAPL,MSFT,<script>"):
            with self.assertRaises(ValueError): parse_tickers(text)

    def test_outage_uses_only_matching_cache(self):
        multi = self.prices.copy()
        multi.columns = pd.MultiIndex.from_product([["Close"], multi.columns])
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as folder, patch.object(market_data, "CACHE", Path(folder)), \
             patch.object(market_data.yf, "set_tz_cache_location"):
            with patch.object(market_data.yf, "download", return_value=multi):
                _, meta = market_data.fetch_prices(["AAPL","MSFT","SPY"],"1y")
                self.assertFalse(meta["cached_fallback"])
            with patch.object(market_data.yf, "download", side_effect=RuntimeError("outage")):
                prices, meta = market_data.fetch_prices(["AAPL","MSFT","SPY"],"1y")
                self.assertTrue(meta["cached_fallback"])
                self.assertEqual(len(prices),3)
                with self.assertRaises(ValueError): market_data.fetch_prices(["AAPL","MSFT","SPY"],"5y")

    def test_custom_range_includes_end_and_isolates_disk_cache(self):
        multi=self.prices.copy()
        multi.columns=pd.MultiIndex.from_product([["Close"],multi.columns])
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as folder, \
             patch.object(market_data,'CACHE',Path(folder)),patch.object(market_data.yf,'set_tz_cache_location'):
            with patch.object(market_data.yf,'download',return_value=multi) as download:
                prices,_=market_data.fetch_prices(['AAPL','MSFT','SPY'],'custom','2025-01-01','2025-01-03')
                self.assertEqual(download.call_args.kwargs['start'],'2025-01-01')
                self.assertEqual(download.call_args.kwargs['end'],'2025-01-04')
                self.assertNotIn('period',download.call_args.kwargs)
                self.assertEqual(prices.index[-1],pd.Timestamp('2025-01-03'))
            with patch.object(market_data.yf,'download',side_effect=RuntimeError('outage')):
                _,meta=market_data.fetch_prices(['AAPL','MSFT','SPY'],'custom','2025-01-01','2025-01-03')
                self.assertTrue(meta['cached_fallback'])
                for start,end in [('2025-01-02','2025-01-03'),('2025-01-01','2025-01-04')]:
                    with self.assertRaises(ValueError):market_data.fetch_prices(['AAPL','MSFT','SPY'],'custom',start,end)

    def test_memory_cache_distinguishes_custom_dates(self):
        market_data._memory.clear()
        self.addCleanup(market_data._memory.clear)
        with patch.object(market_data,'fetch_prices',return_value=(self.prices,{'cached_fallback':False})) as fetch:
            for start,end in [('2025-01-01','2025-01-03'),('2025-01-01','2025-01-03'),
                              ('2025-01-02','2025-01-03'),('2025-01-01','2025-01-04')]:
                market_data.get_prices(['AAPL'],'custom',start_date=start,end_date=end)
            self.assertEqual(fetch.call_count,3)

if __name__ == "__main__":
    unittest.main()
