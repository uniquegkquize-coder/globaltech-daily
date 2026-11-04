import unittest
from scripts.ctr_opportunities import rank

class CTRRankingTests(unittest.TestCase):
    def test_weighted_metrics_and_www_normalization(self):
        rows = [
            {'page':'https://globewiredaily.org/en/news/example/','query':'a','clicks':'1','impressions':'80','position':'5'},
            {'page':'https://www.globewiredaily.org/en/news/example/','query':'b','clicks':'1','impressions':'20','position':'15'},
        ]
        result = rank(rows)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['impressions'], 100)
        self.assertEqual(result[0]['clicks'], 2)
        self.assertEqual(result[0]['ctr'], 0.02)
        self.assertEqual(result[0]['position'], 7)

    def test_invalid_rows(self):
        self.assertEqual(rank([{'page':'https://other.com/','impressions':100,'clicks':0,'position':5}]), [])

if __name__ == '__main__':
    unittest.main()
