import unittest
from src.reasoning.engine import score_college


class ScoringTests(unittest.TestCase):
    def test_score_college_basic(self):
        out = score_college('X', 'CS', alpha=0.6, beta=0.4, sentiment_score=0.5, confidence_multiplier=1.0, raw_roi=1.0, max_roi=2.0)
        # composite = 0.6*0.5*1 + 0.4*(1/2) = 0.3 + 0.2 = 0.5
        self.assertAlmostEqual(out['composite_score'], 0.5, places=4)


if __name__ == '__main__':
    unittest.main()
