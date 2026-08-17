"""Reasoning engine: handlers for rank and situation queries, scoring and caching."""
import hashlib
import json
import math
import os
import re
from pathlib import Path
from typing import Dict, Any, List

try:
    from rapidfuzz import process as rf_process, fuzz as rf_fuzz
except Exception:
    rf_process = None
    rf_fuzz = None

from src.graph.build_graph import load_graph

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
CACHE_FILE = DATA_DIR / "processed" / "query_cache.json"


def _graph_hash(path: Path):
    if not path.exists():
        return None
    with open(path, 'rb') as fh:
        return hashlib.md5(fh.read()).hexdigest()


def _ensure_cache():
    os.makedirs(CACHE_FILE.parent, exist_ok=True)
    if not CACHE_FILE.exists():
        with open(CACHE_FILE, 'w', encoding='utf8') as fh:
            json.dump({}, fh)


def _read_cache():
    _ensure_cache()
    with open(CACHE_FILE, encoding='utf8') as fh:
        return json.load(fh)


def _write_cache(d):
    _ensure_cache()
    with open(CACHE_FILE, 'w', encoding='utf8') as fh:
        json.dump(d, fh, ensure_ascii=False, indent=2)


def generate_cache_key(query_type, colleges=None, courses=None, text=''):
    colleges = tuple(sorted(colleges or []))
    courses = tuple(sorted(courses or []))
    return json.dumps((query_type, colleges, courses, text), sort_keys=True)


def score_college(college: str, course: str = None, alpha: float = 0.6, beta: float = 0.4, sentiment_score: float = 0.0, confidence_multiplier: float = 1.0, raw_roi: float = None, max_roi: float = 2.0) -> Dict[str, Any]:
    """Combine sentiment and ROI into a composite score.

    sentiment_score is expected in [-1.0, 1.0]. ROI is raw ratio (e.g. 1.2).
    The function returns a dict with composite_score and diagnostics.
    """
    norm_roi = (raw_roi or 0.0) / max_roi if raw_roi else 0.0
    composite = (alpha * sentiment_score * confidence_multiplier) + (beta * norm_roi)
    return {
        'college': college,
        'course': course,
        'composite_score': round(composite, 4),
        'sentiment_score': round(sentiment_score, 4),
        'confidence_multiplier': confidence_multiplier,
        'raw_roi': raw_roi,
        'normalized_roi': round(norm_roi, 4)
    }


def _simple_extract_colleges(text: str, graph) -> List[str]:
    # naive alias matching against college node names
    if not graph:
        return []
    names = []
    lower = text.lower()
    # build alias map from actual college nodes
    alias_map = {}
    for node in graph.get('nodes', []):
        if node.get('type') == 'College':
            name = node.get('name')
            if not name:
                continue
            aliases = set([name, *(node.get('aliases') or [])])
            # add normalized variants
            short = ''.join(ch for ch in name if ch.isalnum()).lower()
            aliases.add(short)
            initials = ''.join([p[0] for p in re.split(r"\W+", name) if p])
            if initials:
                aliases.add(initials.lower())
            for a in list(aliases):
                if a:
                    alias_map[a.lower()] = name

    # exact / alias matching
    for a, fullname in alias_map.items():
        if a in lower:
            names.append(fullname)

    if names:
        return sorted(set(names))

    # fuzzy fallback using rapidfuzz if available
    if rf_process is not None:
        choices = list({n.get('name') for n in graph.get('nodes', []) if n.get('type') == 'College' and n.get('name')})
        try:
            match, score, _ = rf_process.extractOne(text, choices, scorer=rf_fuzz.token_sort_ratio)
            if score and score >= 80:
                return [match]
        except Exception:
            pass

    return []


def answer(query_type: str, **kwargs) -> Dict[str, Any]:
    graph_path = DATA_DIR / 'graph' / 'knowledge_graph.json'
    graph_hash = _graph_hash(graph_path)
    use_cache = kwargs.pop('use_cache', True)
    cache_key = generate_cache_key(query_type, kwargs.get('colleges'), kwargs.get('preferred_courses'), kwargs.get('text') or '')

    if use_cache:
        cache = _read_cache()
        entry = cache.get(cache_key)
        if entry and entry.get('graph_version') == graph_hash:
            return {'_cached': True, **entry['result']}

    graph = load_graph(graph_path)

    # Input sanitization
    if query_type == 'rank':
        r = kwargs.get('rank')
        try:
            if r is None:
                raise ValueError('rank is required')
            r = int(r)
            if r <= 0 or r > 1_000_000:
                raise ValueError('rank must be between 1 and 1,000,000')
            kwargs['rank'] = r
        except Exception as e:
            return {'error': 'invalid_rank', 'message': str(e)}
    else:
        text = (kwargs.get('text') or '').strip()
        if not text:
            return {'error': 'invalid_text', 'message': 'empty free-text queries are not allowed'}
        if len(text) > 2000:
            return {'error': 'invalid_text', 'message': 'query too long (max 2000 chars)'}

    # run handler with a timeout to avoid pathological graph traversal
    result_container = {}

    def _worker():
        try:
            if query_type == 'rank':
                result_container['res'] = _handle_rank(graph, **kwargs)
            else:
                result_container['res'] = _handle_situation(graph, **kwargs)
        except Exception as ex:
            result_container['res'] = {'error': 'handler_exception', 'message': str(ex)}

    import threading
    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    thread.join(10.0)  # 10 second timeout for graph traversal
    if thread.is_alive():
        return {'error': 'timeout', 'message': 'query processing exceeded 10s timeout'}
    res = result_container.get('res', {'error': 'no_result'})

    if use_cache:
        cache = _read_cache()
        cache[cache_key] = {'result': res, 'computed_at': int(__import__('time').time()), 'graph_version': graph_hash}
        _write_cache(cache)

    return res


def _node_map(graph):
    return {n.get('id'): n for n in (graph.get('nodes') or [])}


def _top_excerpts(graph: Dict[str, Any], sources: List[str], top_n: int = 2, max_words: int = 25) -> List[Dict[str, Any]]:
    """Return top N excerpts (by credibility) for given comment ids.

    Each excerpt is {'excerpt': str, 'permalink': str, 'credibility': float}.
    """
    if not sources or not graph:
        return []
    nm = _node_map(graph)
    comment_nodes = []
    for cid in sources:
        n = nm.get(cid)
        if not n or n.get('type') != 'Comment':
            continue
        comment_nodes.append((n.get('credibility', 0.0) or 0.0, n))
    comment_nodes.sort(key=lambda x: x[0], reverse=True)
    out = []
    for cred, n in comment_nodes[:top_n]:
        body = (n.get('body') or '').strip()
        words = body.split()
        excerpt = ' '.join(words[:max_words])
        if len(words) > max_words:
            excerpt += '...'
        out.append({'excerpt': excerpt, 'permalink': n.get('permalink'), 'credibility': round(float(cred), 6)})
    return out


# NOTE: For production use the JSON file `data/graph/knowledge_graph.json`
# should be migrated to a proper graph database (e.g. Neo4j) to support
# scalable, transactional queries and safe, cancellable traversals. We
# intentionally keep JSON storage here as a prototype for the internship
# submission; do NOT treat the JSON file as production-grade storage.


def render_simple(result: Dict[str, Any]) -> str:
    # basic paragraph render without excerpts
    colleges = result.get('colleges_considered', [])
    parts = []
    if colleges:
        parts.append('Colleges analyzed: ' + ', '.join(colleges) + '.')
    ss = result.get('sentiment_summary', {})
    if ss:
        topics = []
        for t, info in ss.items():
            score = info.get('score')
            label = info.get('confidence_label')
            if score is None:
                continue
            topics.append(f"{t}: {score} ({label})")
        if topics:
            parts.append('Topic Sentiments: ' + ', '.join(topics) + '.')
    note = result.get('confidence_note')
    if note:
        parts.append(note)
    return ' '.join(parts)


def render_with_excerpts(result: Dict[str, Any], graph: Dict[str, Any]) -> str:
    nm = _node_map(graph)
    colleges = result.get('colleges_considered', [])
    parts = []
    if colleges:
        parts.append('Colleges analyzed: ' + ', '.join(colleges) + '.')
    ss = result.get('sentiment_summary', {})
    if ss:
        topics = []
        for t, info in ss.items():
            score = info.get('score')
            label = info.get('confidence_label')
            sources = info.get('sources') or []
            if score is None:
                continue
            excerpt_parts = []
            # select top 2 by credibility
            comment_nodes = []
            for cid in sources:
                n = nm.get(cid)
                if not n:
                    continue
                comment_nodes.append((n.get('credibility', 0.0) or 0.0, n))
            comment_nodes.sort(key=lambda x: x[0], reverse=True)
            for cred, n in comment_nodes[:2]:
                body = (n.get('body') or '').strip()
                words = body.split()
                excerpt = ' '.join(words[:20])
                if len(words) > 20:
                    excerpt += '...'
                permalink = n.get('permalink') or ''
                if permalink:
                    excerpt_parts.append(f'"{excerpt}" — {permalink}')
                else:
                    excerpt_parts.append(f'"{excerpt}"')
            if excerpt_parts:
                topics.append(f"{t}: {score} ({label}) (see: {', '.join(excerpt_parts)})")
            else:
                topics.append(f"{t}: {score} ({label})")
        if topics:
            parts.append('Topic Sentiments: ' + ', '.join(topics) + '.')
    note = result.get('confidence_note')
    if note:
        parts.append(note)
    return ' '.join(parts)


def _handle_rank(graph, exam=None, rank=None, category=None, preferred_courses=None, **_):
    # Walk RankRecord nodes in graph to find matching colleges. This is a
    # compact implementation assuming graph nodes have been named with a
    # "course::college::" style if present.
    colleges = []
    if not graph:
        return {'colleges_considered': [], 'sentiment_summary': {}, 'agreement_level': 'N/A', 'confidence_note': 'no graph'}

    # simplified: any Course nodes are eligible (we assume cutoffs already applied in graph)
    for node in graph.get('nodes', []):
        if node.get('type') == 'Course':
            colleges.append(node.get('college'))

    colleges = sorted(set([c for c in colleges if c]))
    sentiment_summary = {}
    # placeholders; real aggregation happens elsewhere. include sources list per topic
    for topic in ['placements', 'fees', 'faculty', 'hostel_food', 'campus_life', 'teaching', 'problems', 'branch_regret', 'overall']:
        sentiment_summary[topic] = {'score': None, 'sample_size': 0, 'variance': None, 'confidence_label': 'no data', 'sources': [], 'top_comments': []}

    # ROI analysis per college: collect course node ids as sources if present
    roi_analysis = {}
    for node in graph.get('nodes', []):
        if node.get('type') == 'Course':
            college = node.get('college')
            roi = node.get('roi')
            if college:
                roi_entry = roi_analysis.setdefault(college, {'roi_values': [], 'sources': []})
                if roi is not None:
                    roi_entry['roi_values'].append(roi)
                roi_entry['sources'].append(node.get('id'))
    # collapse roi_analysis to a simple per-college entry (take average if multiple courses)
    for college, ent in roi_analysis.items():
        vals = ent.get('roi_values', [])
        avg_roi = sum(vals) / len(vals) if vals else None
        availability = 'available' if vals and ent.get('sources') else 'insufficient'
        roi_analysis[college] = {'raw_roi': round(avg_roi, 3) if avg_roi is not None else None, 'sources': ent.get('sources', []), 'data_availability': availability}

    # scoring policy used for composite scores
    scoring_policy = {'alpha': 0.6, 'beta': 0.4}

    # indicate whether cutoff/rank data exists
    cutoff_exists = any(n.get('type') == 'RankRecord' for n in (graph.get('nodes') or []))
    confidence_note = 'Based on cutoff data and sentiment aggregation.' if cutoff_exists else 'Cutoff/RankRecord data not available; sentiment-only analysis.'

    return {
        'colleges_considered': colleges,
        'sentiment_summary': sentiment_summary,
        'agreement_level': 'high' if colleges else 'N/A',
        'confidence_note': confidence_note,
        'scoring_policy': scoring_policy,
        'supporting_comment_count': 0,
        'roi_analysis': roi_analysis,
        'cutoff_data_available': bool(cutoff_exists),
    }


def _infer_topic_from_text(text: str) -> str:
    text = (text or '').lower()
    for topic, kws in {
        'placements': ['placement', 'package'],
        'fees': ['fee', 'tuition'],
        'faculty': ['faculty', 'professor'],
        'hostel_food': ['mess', 'food', 'hostel food', 'hostel'],
        'campus_life': ['campus life', 'fest', 'event', 'campus'],
        'teaching': ['teaching', 'lecture', 'faculty'],
        'problems': ['problem', 'issue', 'complaint'],
        'branch_regret': ['regret', 'wish', 'should have']
    }.items():
        if any(k in text for k in kws):
            return topic
    return ''


def _handle_situation(graph, text=None, **_):
    colleges = _simple_extract_colleges(text or '', graph)
    sentiment_summary = {}
    # If no graph or no colleges, try ambiguous topic handling
    if not graph:
        return {'colleges_considered': [], 'sentiment_summary': {}, 'agreement_level': 'low', 'confidence_note': 'No graph available', 'supporting_comment_count': 0}

    if not colleges:
        topic = _infer_topic_from_text(text or '')
        if topic:
            # comparative analysis: compute per-college sentiment for the requested topic
            per_col = {}
            for n in graph.get('nodes', []):
                if n.get('type') == 'Comment':
                    # find discusses edges for this comment
                    for e in graph.get('edges', []):
                        if e.get('u') == n.get('id') and e.get('type') == 'discusses':
                            v = e.get('v')
                            if not v:
                                continue
                            # v looks like 'college::Name'
                            college_name = v.split('::', 1)[-1]
                            body = (n.get('body') or '').lower()
                            kws = {
                                'placements': ['placement', 'package'],
                                'fees': ['fee', 'tuition'],
                                'faculty': ['faculty', 'professor'],
                                'hostel_food': ['mess', 'food', 'hostel food', 'hostel'],
                                'campus_life': ['campus life', 'fest', 'event', 'campus'],
                                'teaching': ['teaching', 'lecture', 'faculty'],
                                'problems': ['problem', 'issue', 'complaint'],
                                'branch_regret': ['regret', 'wish', 'should have']
                            }[topic]
                            if any(k in body for k in kws):
                                ent = per_col.setdefault(college_name, {'polarities': [], 'sources': []})
                                ent['polarities'].append(n.get('polarity', 0.0))
                                ent['sources'].append(n.get('id'))
            ranked = []
            for col, ent in per_col.items():
                vals = ent['polarities']
                if not vals:
                    continue
                mean = sum(vals) / len(vals)
                var = sum((x - mean) ** 2 for x in vals) / len(vals) if len(vals) > 1 else None
                if len(vals) >= 8:
                    label = 'high confidence'
                elif len(vals) >= 3:
                    label = 'moderate confidence'
                else:
                    label = 'low confidence'
                consensus_note = None
                if var is not None and var > 0.35:
                    consensus_note = 'divided / mixed reviews'
                excerpts = _top_excerpts(graph, ent['sources'], top_n=2)
                ranked.append({'college': col, 'score': round(mean, 3), 'sample_size': len(vals), 'variance': var, 'confidence_label': label, 'consensus_note': consensus_note, 'top_comments': excerpts})
            ranked.sort(key=lambda x: x['score'], reverse=True)
            scoring_policy = {'alpha': 0.6, 'beta': 0.4}
            return {'topic': topic, 'ranked_colleges': ranked[:3], 'agreement_level': 'moderate' if ranked else 'low', 'confidence_note': f'Comparison across known colleges for topic "{topic}"', 'supporting_comment_count': sum(len(v.get('sources', [])) for v in per_col.values()), 'scoring_policy': scoring_policy}
        # no topic inferred, return not found
        return {'colleges_considered': [], 'sentiment_summary': {}, 'agreement_level': 'low', 'confidence_note': 'No matching colleges found', 'supporting_comment_count': 0}

    # collect comment polarities for the matched colleges (crude)
    topic_map = {}
    for n in graph.get('nodes', []):
        if n.get('type') == 'Comment':
            # if any discusses edge to matched college exists
            for e in graph.get('edges', []):
                if e.get('u') == n.get('id') and e.get('type') == 'discusses' and e.get('v') in [f"college::{c}" for c in colleges]:
                    polarity = n.get('polarity', 0.0)
                    cid = n.get('id')
                    # naive topic assignment: look for keywords
                    body = (n.get('body') or '').lower()
                    for topic, kws in {
                        'placements': ['placement', 'package'],
                        'fees': ['fee', 'tuition'],
                        'faculty': ['faculty', 'professor'],
                        'hostel_food': ['mess', 'food'],
                        'campus_life': ['campus life', 'fest', 'event'],
                        'teaching': ['teaching', 'lecture', 'faculty'],
                        'problems': ['problem', 'issue', 'complaint'],
                        'branch_regret': ['regret', 'wish', 'should have']
                    }.items():
                        if any(k in body for k in kws):
                            topic_map.setdefault(topic, []).append((polarity, cid))
    # collect ROI sources: look for Course nodes per college
    roi_analysis = {}
    for node in graph.get('nodes', []):
        if node.get('type') == 'Course' and node.get('college') in colleges:
            college = node.get('college')
            roi = node.get('roi')
            ent = roi_analysis.setdefault(college, {'roi_values': [], 'sources': []})
            if roi is not None:
                ent['roi_values'].append(roi)
            ent['sources'].append(node.get('id'))
    for college, ent in roi_analysis.items():
        vals = ent.get('roi_values', [])
        avg_roi = sum(vals) / len(vals) if vals else None
        availability = 'available' if vals and ent.get('sources') else 'insufficient'
        roi_analysis[college] = {'raw_roi': round(avg_roi, 3) if avg_roi is not None else None, 'sources': ent.get('sources', []), 'data_availability': availability}
    for topic, vals in topic_map.items():
        if not vals:
            continue
        # vals is list of (polarity, cid)
        polarities = [v[0] for v in vals]
        sources = [v[1] for v in vals]
        mean = sum(polarities) / len(polarities)
        var = sum((x - mean) ** 2 for x in polarities) / len(polarities) if len(polarities) > 1 else None
        # confidence by sample size
        if len(vals) >= 8:
            label = 'high confidence'
        elif len(vals) >= 3:
            label = 'moderate confidence'
        else:
            label = 'low confidence'
        # consensus vs divided: if variance is high, flag as divided
        consensus_note = None
        if var is not None and var > 0.35:
            consensus_note = 'divided / mixed reviews'
        sentiment_summary[topic] = {'score': round(mean, 3), 'sample_size': len(polarities), 'variance': var, 'confidence_label': label, 'consensus_note': consensus_note, 'sources': sources, 'top_comments': _top_excerpts(graph, sources, top_n=2)}

    return {'colleges_considered': colleges, 'sentiment_summary': sentiment_summary, 'agreement_level': 'moderate', 'confidence_note': 'Based on weighted sentiment and credibility scores.', 'supporting_comment_count': sum(len(v) for v in topic_map.values()), 'roi_analysis': roi_analysis}
