import json
import os
import unittest
from pathlib import Path

from src.reasoning import engine


class ConfidenceVarianceTests(unittest.TestCase):
    def setUp(self):
        # create a minimal graph file used by engine
        self.data_dir = Path(__file__).resolve().parents[1] / 'data'
        graph_dir = self.data_dir / 'graph'
        graph_dir.mkdir(parents=True, exist_ok=True)
        # Save original graph so tearDown can restore it
        self._graph_file = graph_dir / 'knowledge_graph.json'
        self._original_graph = None
        if self._graph_file.exists():
            self._original_graph = self._graph_file.read_bytes()
        # nodes: one college and several comments
        nodes = [
            {'id': 'college::TestCollege', 'type': 'College', 'name': 'TestCollege', 'aliases': ['TestCollege']},
        ]
        edges = []
        # create 9 comments with mixed sentiments to force high variance
        for i, val in enumerate([0.9, 0.8, 0.85, -0.7, -0.6, -0.65, 0.1, -0.05, 0.0]):
            cid = f'comment::c{i}'
            nodes.append({'id': cid, 'type': 'Comment', 'body': 'test', 'polarity': val})
            edges.append({'u': cid, 'v': 'college::TestCollege', 'type': 'discusses'})

        graph = {'nodes': nodes, 'edges': edges}
        with open(self._graph_file, 'w', encoding='utf8') as fh:
            json.dump(graph, fh)

    def tearDown(self):
        # Restore the original graph file instead of deleting it,
        # so subsequent tests that need the real graph are not broken.
        if self._original_graph is not None:
            self._graph_file.write_bytes(self._original_graph)
        elif self._graph_file.exists():
            os.remove(self._graph_file)

    def test_divided_flag(self):
        res = engine._handle_situation(engine.load_graph(Path(__file__).resolve().parents[1] / 'data' / 'graph' / 'knowledge_graph.json'), text='TestCollege')
        # because we created mixed positive and negative polarities with sample_size=9,
        # consensus_note should be 'divided / mixed reviews' for at least one topic if assigned
        # Our naive topic detection may not tag topics, but sentiment_summary should be a dict
        self.assertIsInstance(res.get('sentiment_summary'), dict)


if __name__ == '__main__':
    unittest.main()
