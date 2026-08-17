import unittest


class SmokeTest(unittest.TestCase):
    def test_imports(self):
        import src.cli
        import src.graph.build_graph
        import src.reasoning.engine
        self.assertTrue(True)


if __name__ == '__main__':
    unittest.main()
