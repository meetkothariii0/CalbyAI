import json
import os
import time
import unittest
from pathlib import Path

from src.reasoning import engine


class CacheLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.data_dir = Path(__file__).resolve().parents[1] / 'data'
        graph_dir = self.data_dir / 'graph'
        graph_dir.mkdir(parents=True, exist_ok=True)
        # Save original graph so tearDown can restore it
        self._graph_file = graph_dir / 'knowledge_graph.json'
        self._original_graph = None
        if self._graph_file.exists():
            self._original_graph = self._graph_file.read_bytes()
        # Write minimal test graph
        nodes = [
            {'id': 'college::A', 'type': 'College', 'name': 'A', 'aliases': ['A']},
            {'id': 'comment::c1', 'type': 'Comment', 'body': 'good', 'polarity': 0.5},
        ]
        edges = [
            {'u': 'comment::c1', 'v': 'college::A', 'type': 'discusses'}
        ]
        with open(self._graph_file, 'w', encoding='utf8') as fh:
            json.dump({'nodes': nodes, 'edges': edges}, fh)
        # remove cache
        cache_file = self.data_dir / 'processed' / 'query_cache.json'
        if cache_file.exists():
            os.remove(cache_file)

    def tearDown(self):
        cache_file = self.data_dir / 'processed' / 'query_cache.json'
        if cache_file.exists():
            os.remove(cache_file)
        # Restore the original graph file instead of deleting it,
        # so subsequent tests that need the real graph are not broken.
        if self._original_graph is not None:
            self._graph_file.write_bytes(self._original_graph)
        elif self._graph_file.exists():
            os.remove(self._graph_file)

    def test_cache_lifecycle(self):
        # first call should compute and cache
        r1 = engine.answer('situation', text='A', use_cache=True)
        self.assertFalse(r1.get('_cached', False))
        # second call should be cached
        r2 = engine.answer('situation', text='A', use_cache=True)
        self.assertTrue(r2.get('_cached', False))
        # modify graph file to change hash
        graph_file = self.data_dir / 'graph' / 'knowledge_graph.json'
        with open(graph_file, 'a', encoding='utf8') as fh:
            fh.write(' ')  # touch
        time.sleep(0.1)
        r3 = engine.answer('situation', text='A', use_cache=True)
        # after graph change it should not be cached (implementation returns fresh result without _cached)
        self.assertFalse(r3.get('_cached', False))


if __name__ == '__main__':
    unittest.main()
