import unittest

from src.reasoning.engine import answer


class TestAliasResolution(unittest.TestCase):
    def test_alias_rvce(self):
        res = answer('situation', text='How are placements at RVCE?', use_cache=False)
        self.assertIsInstance(res, dict)
        self.assertIn('RV College of Engineering', res.get('colleges_considered', []))

    def test_alias_rvce_variant(self):
        # fuzzy / spaced variant
        res = answer('situation', text='Tell me about placements at R V College', use_cache=False)
        self.assertIn('RV College of Engineering', res.get('colleges_considered', []))

    def test_alias_pesu_lowercase(self):
        res = answer('situation', text='placements at pesu', use_cache=False)
        self.assertIn('PES University', res.get('colleges_considered', []))

    def test_alias_msrit_case_insensitive(self):
        res = answer('situation', text='MSRIT hostel food', use_cache=False)
        self.assertIn('MSRIT', res.get('colleges_considered', []))

    def test_alias_sirmvit_short(self):
        res = answer('situation', text='How is SirMVIT teaching?', use_cache=False)
        self.assertIn('SirMVIT', res.get('colleges_considered', []))


if __name__ == '__main__':
    unittest.main()
