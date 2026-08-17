import json
import os
import unittest
from pathlib import Path

from src.reasoning import engine


class MissingBranchDataTest(unittest.TestCase):
    def setUp(self):
        self.data_dir = Path(__file__).resolve().parents[1] / 'data'
        graph_dir = self.data_dir / 'graph'
        graph_dir.mkdir(parents=True, exist_ok=True)
        # Save original graph so tearDown can restore it
        self._graph_file = graph_dir / 'knowledge_graph.json'
        self._original_graph = None
        if self._graph_file.exists():
            self._original_graph = self._graph_file.read_bytes()
        # Create a college and a Course node WITHOUT sources or average_package
        nodes = [
            {'id': 'college::NoSourceCollege', 'type': 'College', 'name': 'NoSourceCollege', 'aliases': ['NoSourceCollege'], 'fees': 10.0},
            {'id': 'course::NoSourceCollege::Civil', 'type': 'Course', 'name': 'Civil', 'college': 'NoSourceCollege', 'fees': 10.0}
        ]
        edges = [
            {'u': 'college::NoSourceCollege', 'v': 'course::NoSourceCollege::Civil', 'type': 'offers_course'}
        ]
        with open(self._graph_file, 'w', encoding='utf8') as fh:
            json.dump({'nodes': nodes, 'edges': edges}, fh)

    def tearDown(self):
        # Restore the original graph file instead of deleting it,
        # so subsequent tests that need the real graph are not broken.
        if self._original_graph is not None:
            self._graph_file.write_bytes(self._original_graph)
        elif self._graph_file.exists():
            os.remove(self._graph_file)

    def test_missing_branch_data(self):
        res = engine.answer('situation', text='NoSourceCollege', use_cache=False)
        # ROI should be absent and marked insufficient
        roi = res.get('roi_analysis', {}).get('NoSourceCollege')
        self.assertIsNotNone(roi)
        self.assertIsNone(roi.get('raw_roi'))
        self.assertEqual(roi.get('data_availability'), 'insufficient')


if __name__ == '__main__':
    unittest.main()
