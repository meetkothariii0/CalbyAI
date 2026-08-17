import json
from pathlib import Path

from src.reasoning.engine import answer


def test_grounding_novel_alias():
    # Uses the committed canonical snapshot in data/graph/knowledge_graph.json
    repo_root = Path(__file__).resolve().parents[1]
    graph_file = repo_root / 'data' / 'graph' / 'knowledge_graph.json'
    assert graph_file.exists(), 'canonical knowledge_graph.json snapshot missing'

    # Query with an alias that should match the College 'Xenon Institute'
    res = answer('situation', text='How are placements at Xenon Institute?', use_cache=False)
    assert isinstance(res, dict)
    # It should find the college and include sources in sentiment_summary entries (if any)
    assert 'colleges_considered' in res
    assert 'Xenon Institute' in res.get('colleges_considered', [])
    # Because the snapshot has comment::c1 and comment::c2 discussing the college,
    # supporting_comment_count should be > 0
    assert res.get('supporting_comment_count', 0) > 0
    # roi_analysis should include the college with data_availability 'available'
    roi = res.get('roi_analysis', {}).get('Xenon Institute')
    assert roi is not None and roi.get('data_availability') == 'available'
