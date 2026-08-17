import unittest
import networkx as nx


class PageRankCommunityTests(unittest.TestCase):
    def test_pagerank_corroboration(self):
        G = nx.DiGraph()
        # A is high-credibility isolated
        G.add_node('A')
        G.add_node('B')
        G.add_node('C1')
        G.add_node('C2')
        G.add_node('C3')
        # edges: many nodes point to B
        G.add_edge('C1', 'B')
        G.add_edge('C2', 'B')
        G.add_edge('C3', 'B')
        # weights can be uniform
        pr = nx.pagerank(G)
        # B should have higher pagerank than A
        self.assertGreater(pr['B'], pr.get('A', 0))

    def test_pagerank_sum(self):
        G = nx.DiGraph()
        for i in range(5):
            G.add_node(str(i))
        G.add_edges_from([('0','1'),('1','2'),('2','3'),('3','4'),('4','0')])
        pr = nx.pagerank(G)
        total = sum(pr.values())
        self.assertAlmostEqual(total, 1.0, places=6)


if __name__ == '__main__':
    unittest.main()
