import unittest
from pathlib import Path
import json

from src.graph.build_graph import load_graph, build_graph


class ProvenanceTests(unittest.TestCase):
    def test_course_provenance_and_rankrecord_sources(self):
        """Every Course node with numeric data should have sources referencing data/raw/.
        And every RankRecord should have a sources list referencing cutoffs.csv rows.
        """
        graph = load_graph()
        # If graph not present (test ordering), build a fresh graph from available raw data
        if graph is None:
            build_graph()
            graph = load_graph()
        self.assertIsNotNone(graph, "knowledge_graph.json must exist for tests")
        nodes = {n['id']: n for n in graph.get('nodes', [])}

        # Check Course nodes
        for nid, data in nodes.items():
            if data.get('type') == 'Course':
                avg = data.get('average_package')
                roi = data.get('roi')
                sources = data.get('sources') or []
                # If numeric fields are present, require at least one source pointing to data/raw
                if (avg is not None) or (roi is not None):
                    self.assertTrue(len(sources) >= 1, f"Course node {nid} has numeric data but no sources")
                    import os
                    raw_fragment = os.path.join('data', 'raw')
                    for s in sources:
                        self.assertIn(raw_fragment, str(s), f"Course source {s} should reference data/raw")

        # Check RankRecord nodes
        for nid, data in nodes.items():
            if data.get('type') == 'RankRecord':
                sources = data.get('sources') or []
                self.assertTrue(len(sources) >= 1, f"RankRecord {nid} must have a sources list")
                found_cutoff = any('cutoffs.csv' in str(s) or 'cutoffs' in str(s) for s in sources)
                self.assertTrue(found_cutoff, f"RankRecord {nid} sources should reference cutoffs.csv row")


if __name__ == '__main__':
    unittest.main()
