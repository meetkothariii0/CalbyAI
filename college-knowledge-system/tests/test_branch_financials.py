import unittest

from src.graph.build_graph import compute_roi


class BranchFinancialsTests(unittest.TestCase):
    def test_compute_roi_valid(self):
        self.assertAlmostEqual(compute_roi(20.0, 11.2), 20.0 / 11.2, places=6)

    def test_compute_roi_missing(self):
        self.assertIsNone(compute_roi(None, 10))
        self.assertIsNone(compute_roi(10, None))
        self.assertIsNone(compute_roi(10, 0))


if __name__ == '__main__':
    unittest.main()
