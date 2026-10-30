"""Application contract tests. Data provider is mocked; no external requests."""
import unittest
from unittest.mock import patch
from datetime import date, timedelta
import numpy as np
import pandas as pd
from service import analyze, distribute
from market_data import search_stocks, _search_cache


def fake_prices(tickers, period, refresh=False, start_date=None, end_date=None):
    paths={"AAPL":[100,110,121],"MSFT":[100,90,81],"SPY":[100,100,100]}
    return pd.DataFrame({s:paths.get(s,[100,105,110]) for s in set([*tickers,"SPY"])},
                        index=pd.date_range("2025-01-01",periods=3)),{
        "retrieved_utc":"2025-01-04T00:00:00+00:00","cached_fallback":False}

class AppTests(unittest.TestCase):
    def setUp(self):
        self.payload={"holdings":[{"symbol":s,"name":s} for s in ["AAPL","MSFT","SPY"]],
                      "weights":[3334,3333,3333],"period":"5y","risk_free":0}
        self.patch=patch('service.get_prices',side_effect=fake_prices)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_exact_assignment_mix(self):
        self.payload['action']={'type':'weights','weights':[4000,3500,2500]}
        result=analyze(self.payload)
        self.assertEqual(result['weights'],[4000,3500,2500])
        self.assertAlmostEqual(result['metrics']['Total return'],.0175)
        self.assertEqual(len(result['metrics']),4)
        self.assertAlmostEqual(sum(result['ending_weights']),1)

    def test_draft_cannot_apply_until_exactly_100(self):
        self.payload['action']={'type':'weights','weights':[4000,3500,3333]}
        with self.assertRaises(ValueError):analyze(self.payload)
        self.assertEqual(self.payload['weights'],[3334,3333,3333])

    def test_adding_preserves_existing_proportions(self):
        self.payload['weights']=[4000,3500,2500]
        self.payload['action']={'type':'add','holding':{'symbol':'NVDA','name':'NVIDIA'}}
        result=analyze(self.payload)
        self.assertEqual(result['weights'],[3000,2625,1875,2500])
        self.assertEqual(len(result['holdings']),4)

    def test_failed_download_does_not_mutate_input(self):
        self.payload['action']={'type':'add','holding':{'symbol':'BAD'}}
        with patch('service.get_prices',side_effect=ValueError('No data')):
            with self.assertRaises(ValueError):analyze(self.payload)
        self.assertEqual(len(self.payload['holdings']),3)
        self.assertEqual(self.payload['weights'],[3334,3333,3333])

    def test_removing_redistributes(self):
        self.payload['weights']=[4000,3500,2500]
        self.payload['action']={'type':'remove','index':2}
        result=analyze(self.payload)
        self.assertEqual(result['weights'],[5333,4667])
        # Requests must not mutate the caller's state, even on success.
        self.assertEqual(self.payload['weights'],[4000,3500,2500])

    def test_random_mix_and_rounding(self):
        for n in [1,2,3,7,17,30]:
            weights=distribute(10000,[1]*n)
            self.assertEqual(sum(weights),10000)
            self.assertLessEqual(max(weights)-min(weights),1)
        self.payload['action']={'type':'random','count':17}
        result=analyze(self.payload)
        self.assertEqual(len(set(h['symbol'] for h in result['holdings'])),17)
        self.assertEqual(sum(result['weights']),10000)

    def test_one_stock_random_mix(self):
        self.payload['action']={'type':'random','count':1}
        result=analyze(self.payload)
        self.assertEqual(len(result['holdings']),1)
        self.assertEqual(result['weights'],[10000])
        self.assertIsNone(result['correlation'])
        np.testing.assert_allclose(result['portfolio'],result['series'][result['holdings'][0]['symbol']])
        for n in (0,31,True):
            self.payload['action']['count']=n
            with self.assertRaises(ValueError):analyze(self.payload)

    def test_custom_dates_rebase_all_series_to_same_window(self):
        self.payload.update(period='custom',start_date='2025-01-02',end_date='2025-01-04',weights=[4000,3500,2500])
        raw=pd.DataFrame({'AAPL':[1,100,110,121,900], 'MSFT':[900,100,90,81,1],
                          'SPY':[1,100,100,100,900]},index=pd.date_range('2025-01-01',periods=5))
        with patch('service.get_prices',return_value=(raw,{'cached_fallback':False})) as provider:
            result=analyze(self.payload)
        self.assertEqual(result['dates'],['2025-01-02','2025-01-03','2025-01-04'])
        self.assertAlmostEqual(result['metrics']['Total return'],.0175)
        self.assertEqual(result['benchmark_metrics']['Total return'],0)
        self.assertEqual(result['start_date'],'2025-01-02')
        self.assertEqual(provider.call_args.kwargs['end_date'],'2025-01-04')

    def test_invalid_custom_dates_rejected_before_download(self):
        self.payload['period']='custom'
        bad_ranges=[('', '2025-01-03'),('2025-02-30','2025-03-04'),
                    ('2025-01-03','2025-01-03'),('2025-01-04','2025-01-03'),
                    ('1899-01-01','2025-01-03'),('2025-01-01',(date.today()+timedelta(days=1)).isoformat())]
        with patch('service.get_prices') as provider:
            for start,end in bad_ranges:
                self.payload.update(start_date=start,end_date=end)
                with self.subTest(start=start,end=end),self.assertRaises(ValueError):analyze(self.payload)
            provider.assert_not_called()

    def test_custom_dates_need_three_common_prices(self):
        self.payload.update(period='custom',start_date='2025-01-02',end_date='2025-01-03')
        with self.assertRaisesRegex(ValueError,'Not enough overlapping'):analyze(self.payload)

    def test_custom_dates_survive_adding_a_holding(self):
        self.payload.update(period='custom',start_date='2025-01-01',end_date='2025-01-03',
                            action={'type':'add','holding':{'symbol':'NVDA'}})
        result=analyze(self.payload)
        self.assertEqual(result['end_date'],'2025-01-03')
        self.assertEqual(result['dates'],['2025-01-01','2025-01-02','2025-01-03'])
        self.assertEqual(len(result['holdings']),4)

    def test_duplicate_and_invalid_inputs(self):
        self.payload['action']={'type':'add','holding':{'symbol':'AAPL'}}
        with self.assertRaises(ValueError):analyze(self.payload)
        self.payload['action']=None
        for invalid in [[0,0,0],[-1,5000,5001],[float('nan'),5000,5000]]:
            self.payload['weights']=invalid
            with self.assertRaises(ValueError):analyze(self.payload)

    def test_zero_weight_stock_not_in_average_correlation(self):
        self.payload['weights']=[10000,0,0]
        result=analyze(self.payload)
        self.assertIsNone(result['correlation'])
        self.assertAlmostEqual(result['metrics']['Total return'],.21)

    def test_search_returns_names_and_filters_foreign_non_equity(self):
        _search_cache.clear()
        quotes=[{'symbol':'AAPL','longname':'Apple Inc.','quoteType':'EQUITY','exchange':'NMS','exchDisp':'NASDAQ'},
                {'symbol':'AAPL.L','quoteType':'EQUITY','exchange':'LSE'},
                {'symbol':'BTC-USD','quoteType':'CRYPTOCURRENCY','exchange':'CCC'}]
        with patch('market_data.yf.Search') as search:
            search.return_value.quotes=quotes
            result=search_stocks('apple')
            self.assertEqual(result,[{'symbol':'AAPL','name':'Apple Inc.','exchange':'NASDAQ','type':'EQUITY'}])
            self.assertEqual(search_stocks('apple'),result)
            self.assertEqual(search.call_count,1)

if __name__=='__main__':unittest.main()
