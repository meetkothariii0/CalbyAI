import math
import time
import unittest

from src.graph.build_graph import _decay_factor


class DecayTests(unittest.TestCase):
    def test_fresh(self):
        now = time.time()
        self.assertAlmostEqual(_decay_factor(now, lam=0.15, now=now), 1.0, places=6)

    def test_five_years(self):
        now = time.time()
        five_years = now - 5 * 365.25 * 86400
        d = _decay_factor(five_years, lam=0.15, now=now)
        self.assertAlmostEqual(d, math.exp(-0.15 * 5), places=5)

    def test_ten_years(self):
        now = time.time()
        ten_years = now - 10 * 365.25 * 86400
        d = _decay_factor(ten_years, lam=0.15, now=now)
        self.assertAlmostEqual(d, math.exp(-0.15 * 10), places=5)


if __name__ == '__main__':
    unittest.main()
