from pathlib import Path

from src.reasoning.engine import answer


def test_grounding_novel_alias():
    """Verify that a known alias resolves to the correct college and returns
    grounded results backed by real comments from the knowledge graph."""
    res = answer('situation', text='How are placements at RVCE?', use_cache=False)

    assert isinstance(res, dict), f"Expected dict, got: {type(res)}"
    assert res.get('confidence_note') != 'No graph available', (
        "Graph failed to load — check data/graph/knowledge_graph.json exists"
    )

    # Should resolve to the full college name
    assert 'colleges_considered' in res
    assert 'RV College of Engineering' in res.get('colleges_considered', []), (
        f"RVCE not found in: {res.get('colleges_considered')}"
    )

    # Must have at least one comment backing the result
    assert res.get('supporting_comment_count', 0) > 0

    # Each sentiment entry must include a sources list (provenance enforcement)
    for topic, data in res.get('sentiment_summary', {}).items():
        assert 'sources' in data, f"Missing sources for topic: {topic}"
        assert len(data['sources']) > 0, f"Empty sources list for topic: {topic}"
