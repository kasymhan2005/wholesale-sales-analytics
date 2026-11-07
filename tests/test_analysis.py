import unittest
from pathlib import Path
import pandas as pd
from src.analysis import load_data, analyze, match_reorders, abc_classify

ROOT = Path(__file__).resolve().parents[1]


class AnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.full, cls.products, _, _ = load_data(ROOT/'data/raw')
        cls.results = analyze(cls.full, cls.products)

    def test_source_counts(self):
        self.assertEqual(len(self.full), 4603)
        self.assertEqual(self.full.order_id.nunique(), 346)
        self.assertEqual(len(self.products), 1677)

    def test_revenue_independent_order_calculation(self):
        rows = self.full[self.full.status.eq('confirmed')]
        from decimal import Decimal
        independent = sum(Decimal(str(r.price))*Decimal(str(r.currency_rate))*int(r.quantity)
                          for r in rows.itertuples())
        self.assertAlmostEqual(float(independent), self.results['summary']['revenue'], places=5)
        for key in ['daily','brands','categories','clients','managers','product_sales']:
            self.assertAlmostEqual(self.results[key].revenue.sum(), float(independent), places=5)

    def test_denominators_and_missing_days(self):
        s = self.results['summary']
        self.assertEqual(s['confirmed_orders'] + s['canceled_orders'], s['orders'])
        self.assertAlmostEqual(s['average_order_value'], s['revenue']/s['confirmed_orders'])
        self.assertEqual(len(self.results['daily']), 31)
        no_sales = self.results['daily'].query('confirmed == 0')
        self.assertTrue(no_sales.average_order_value.isna().all())

    def test_pairs_are_unique_and_exact(self):
        pairs = self.results['pairs']
        self.assertFalse(pairs.order_id_canceled.duplicated().any())
        self.assertFalse(pairs.order_id_confirmed.duplicated().any())
        self.assertTrue((pairs.date_confirmed-pairs.date_canceled).eq(pd.Timedelta(days=1)).all())

    def test_same_totals_different_baskets_do_not_match(self):
        rows=[]
        for order,date,status,items in [('a','2024-03-01','canceled',[(1,2),(2,3)]),
                                        ('b','2024-03-02','confirmed',[(1,3),(2,2)])]:
            for product,qty in items:
                rows.append(dict(order_id=order,date=pd.Timestamp(date),status=status,
                    manager='Test',client_id=1,product_id=product,quantity=qty,revenue=qty))
        self.assertEqual(len(match_reorders(pd.DataFrame(rows))),0)

    def test_identical_candidates_are_not_cartesian_product(self):
        rows=[]
        for order,date,status in [('a','2024-03-01','canceled'),('b','2024-03-01','canceled'),
                                  ('c','2024-03-02','confirmed'),('d','2024-03-02','confirmed')]:
            rows.append(dict(order_id=order,date=pd.Timestamp(date),status=status,
                manager='Test',client_id=1,product_id=1,quantity=2,revenue=2))
        pairs=match_reorders(pd.DataFrame(rows))
        self.assertEqual(len(pairs),2)
        self.assertTrue(pairs.ambiguous.all())

    def test_abc_thresholds_and_zero_sales(self):
        p=abc_classify(pd.DataFrame({'id':[1,2,3,4],'revenue':[80.,15.,5.,0.]}))
        self.assertEqual(p.abc.tolist(),['A','B','C','No sales'])
        zero=abc_classify(pd.DataFrame({'id':[1], 'revenue':[0.]}))
        self.assertEqual(zero.iloc[0].abc,'No sales')

if __name__ == '__main__':
    unittest.main()
