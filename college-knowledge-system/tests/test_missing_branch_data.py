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
        # Create a college and a Course node WITHOUT sources or average_package
        nodes = [
            {'id': 'college::NoSourceCollege', 'type': 'College', 'name': 'NoSourceCollege', 'aliases': ['NoSourceCollege'], 'fees': 10.0},
            {'id': 'course::NoSourceCollege::Civil', 'type': 'Course', 'name': 'Civil', 'college': 'NoSourceCollege', 'fees': 10.0}
        ]
        edges = [
            {'u': 'college::NoSourceCollege', 'v': 'course::NoSourceCollege::Civil', 'type': 'offers_course'}
        ]
        with open(graph_dir / 'knowledge_graph.json', 'w', encoding='utf8') as fh:
            json.dump({'nodes': nodes, 'edges': edges}, fh)

    def tearDown(self):
        graph_file = Path(__file__).resolve().parents[1] / 'data' / 'graph' / 'knowledge_graph.json'
        if graph_file.exists():
            os.remove(graph_file)

    def test_missing_branch_data(self):
        res = engine.answer('situation', text='NoSourceCollege', use_cache=False)
        # ROI should be absent and marked insufficient
        roi = res.get('roi_analysis', {}).get('NoSourceCollege')
        self.assertIsNotNone(roi)
        self.assertIsNone(roi.get('raw_roi'))
        self.assertEqual(roi.get('data_availability'), 'insufficient')


if __name__ == '__main__':
    unittest.main()
