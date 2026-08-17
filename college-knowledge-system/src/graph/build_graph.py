"""Build a simple knowledge graph from raw json and CSVs.

This is a compact implementation that captures the key behaviours described in
the review conversation: ingest reddit JSON lines, ingest branch package CSV,
compute credibility with time decay, compute ROI per (college, course), and
persist the graph as JSON.
"""
import csv
import hashlib
import json
import math
import os
from datetime import datetime
from pathlib import Path

import networkx as nx
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
try:
    from rapidfuzz import process, fuzz
except Exception:
    process = None
    fuzz = None


DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def _decay_factor(created_utc, lam=0.15, now=None):
    if created_utc is None:
        return 1.0
    if now is None:
        now = datetime.utcnow().timestamp()
    seconds = max(0.0, now - float(created_utc))
    years = seconds / (365.25 * 86400.0)
    return math.exp(-lam * years)


def _credibility(score, replies, created_utc, lam=0.15, now=None):
    s = max(0, score or 0)
    r = max(0, replies or 0)
    base = math.log(s + 1.0) + 0.5 * math.log(r + 1.0)
    return base * _decay_factor(created_utc, lam=lam, now=now)


def build_graph(raw_reddit_path=None, branch_csv=None, cutoffs_csv=None, out_path=None, force_example=False, data_dir=None):
    G = nx.MultiDiGraph()
    # When tests pass a temporary data_dir, interpret it as the repository root
    # so the function looks under <data_dir>/data/raw (matching real repo layout).
    if data_dir:
        base_data_dir = Path(data_dir) / 'data'
    else:
        base_data_dir = DATA_DIR
    raw_reddit_path = raw_reddit_path or base_data_dir / "raw" / "reddit_raw.jsonl"
    branch_csv = branch_csv or base_data_dir / "raw" / "branch_packages.csv"
    cutoffs_csv = cutoffs_csv or base_data_dir / "raw" / "cutoffs.csv"
    out_path = out_path or base_data_dir / "graph" / "knowledge_graph.json"

    analyzer = SentimentIntensityAnalyzer()

    # build a mapping from subreddit token -> canonical college name by scanning
    # files under data/raw/. This helps connect Comment nodes (which have a
    # `subreddit` field like 'rvce' or 'BMSCE') to College nodes.
    subreddit_to_college = {}
    raw_dir = base_data_dir / 'raw'
    if raw_dir.exists():
        # known token -> full name overrides for common colleges present in the dump
        known_map = {
            'rvce': 'RV College of Engineering',
            'bmsce': 'BMS College of Engineering',
            'pesu': 'PES University',
            'msrit': 'MSRIT',
            'dsce': 'DSCE',
            'bitbangalore': 'BIT Bangalore',
            'bitbangalore': 'BIT Bangalore',
            'sirmvit': 'SirMVIT',
            'nmit': 'NMIT',
            'nhce': 'NHCE',
            'cmrit': 'CMRIT',
            'bmsit': 'BMSIT',
            'rnsit': 'RNSIT',
            'acharya': 'Acharya',
            'mitblr': 'MITBlr'
        }
        # tokens to ignore because they represent exams or other non-college topics
        exam_blacklist = {'kcet'}
        for p in raw_dir.iterdir():
            stem = p.stem  # e.g. '1-rvce-posts' or 'rvce-posts' or 'rvce'
            # skip files that are clearly exam-related (e.g., 'KCET-exam-posts')
            if 'exam' in stem.lower():
                continue
            parts = stem.split('-')
            token = None
            if len(parts) >= 3 and parts[0].isdigit():
                token = parts[1]
            elif len(parts) >= 2:
                # prefer first non-numeric token
                token = parts[0] if not parts[0].isdigit() else parts[1]
            else:
                token = stem
            token_norm = ''.join(ch for ch in token if ch.isalnum()).lower()
            if not token_norm:
                continue
            if token_norm in known_map:
                subreddit_to_college[token_norm] = known_map[token_norm]
            else:
                # default canonicalization: Title-case the token (RVCE -> Rvce -> Rvce)
                # better than leaving lowercase; keep token in upper form when short
                if token_norm.isupper() or len(token_norm) <= 5:
                    subreddit_to_college[token_norm] = token_norm.upper()
                else:
                    subreddit_to_college[token_norm] = token_norm.replace('_', ' ').title()

    # ingest branch packages
    if Path(branch_csv).exists():
        with open(branch_csv, newline='', encoding='utf8') as fh:
            reader = csv.DictReader(fh)
            for idx, row in enumerate(reader, start=1):
                college = row.get('college')
                course = row.get('course')
                try:
                    avg_pkg = float(row.get('average_package_lpa') or 0)
                except Exception:
                    avg_pkg = None
                try:
                    fees = float(row.get('fees_lakhs') or 0)
                except Exception:
                    fees = None
                college_id = f"college::{college}"
                course_id = f"course::{college}::{course}"
                # attach source info so ROI/package can be traced
                G.add_node(college_id, type='College', name=college, aliases=[college], fees=fees)
                G.add_node(course_id, type='Course', name=course, college=college, average_package=avg_pkg, fees=fees, sources=[f"{branch_csv}:{idx}"])
                G.add_edge(college_id, course_id, type='offers_course')

    # ingest reddit
    if Path(raw_reddit_path).exists():
        now_ts = datetime.utcnow().timestamp()
        # prepare fuzzy matcher choices from existing college nodes (if rapidfuzz available)
        college_name_to_id = {}
        for n, d in G.nodes(data=True):
            if d.get('type') == 'College':
                name = d.get('name')
                if name:
                    college_name_to_id[name] = n
        with open(raw_reddit_path, encoding='utf8') as fh:
            for line in fh:
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                cid = obj.get('id') or obj.get('name') or f"c_{hashlib.md5(line.encode()).hexdigest()}"
                node_id = f"comment::{cid}"
                body = obj.get('body') or obj.get('selftext') or obj.get('title') or ''
                score = obj.get('score') or obj.get('ups') or 0
                replies = obj.get('num_replies') or 0
                created = obj.get('created_utc')
                permalink = obj.get('permalink')
                polarity = analyzer.polarity_scores(body)['compound'] if body else 0.0
                cred = _credibility(score, replies, created, now=now_ts)
                G.add_node(node_id, type='Comment', body=body, score=score, num_replies=replies, created_utc=created, polarity=polarity, credibility=cred, permalink=permalink)
                # crude college mention mapping: match subreddit token against the
                # subreddit_to_college map we built from file prefixes and known_map.
                subreddit = (obj.get('subreddit') or '').strip()
                if subreddit:
                    token_norm = ''.join(ch for ch in subreddit if ch.isalnum()).lower()
                    mapped_name = subreddit_to_college.get(token_norm)
                    if mapped_name:
                        college_id = f"college::{mapped_name}"
                        # ensure college node exists with canonical name + alias
                        if college_id not in G:
                            G.add_node(college_id, type='College', name=mapped_name, aliases=[subreddit])
                        G.add_edge(node_id, college_id, type='discusses')

                # fuzzy match body/title against known college names (if rapidfuzz available)
                if process is not None and body:
                    try:
                        # use token_sort_ratio for robust matching
                        choice, score, _ = process.extractOne(body, list(college_name_to_id.keys()), scorer=fuzz.token_sort_ratio)
                        if score and score >= 80:
                            matched_college_id = college_name_to_id.get(choice)
                            if matched_college_id:
                                G.add_edge(node_id, matched_college_id, type='discusses', match_score=score)
                    except Exception:
                        pass

    # ingest cutoffs into RankRecord nodes (provenance preserved per-row)
    if Path(cutoffs_csv).exists():
        with open(cutoffs_csv, newline='', encoding='utf8') as fh:
            reader = csv.DictReader(fh)
            for idx, row in enumerate(reader, start=1):
                college = row.get('college')
                course = row.get('course')
                exam = row.get('exam')
                year = row.get('year')
                category = row.get('category')
                closing = row.get('closing_rank') or row.get('closing')
                roundv = row.get('round')
                source_type = row.get('source_type')
                source_note = row.get('source_note')
                # parse numeric closing rank when possible, else None
                try:
                    if closing is None or closing == '' or str(closing).upper() == 'NA':
                        closing_rank = None
                    else:
                        closing_rank = int(float(str(closing).strip()))
                except Exception:
                    closing_rank = None

                # stable id for the rank record
                rank_id = f"rank::{college}::{course}::{exam}::{year}::{idx}"
                G.add_node(
                    rank_id,
                    type='RankRecord',
                    college=college,
                    course=course,
                    exam=exam,
                    year=year,
                    category=category,
                    closing_rank=closing_rank,
                    round=roundv,
                    source_type=source_type,
                    source_note=source_note,
                    sources=[f"{cutoffs_csv}:{idx}"]
                )

                # ensure college/course nodes exist so edges have concrete targets
                course_id = f"course::{college}::{course}"
                college_id = f"college::{college}"
                if course_id not in G:
                    G.add_node(course_id, type='Course', name=course, college=college, average_package=None, fees=None, data_availability='insufficient', sources=[])
                if college_id not in G:
                    G.add_node(college_id, type='College', name=college, aliases=[college])
                # connect rank -> course/college
                G.add_edge(rank_id, course_id, type='resulted_in_admission_to')
                G.add_edge(rank_id, college_id, type='applies_to_college')

    # compute ROI per course if not already
    for n, data in list(G.nodes(data=True)):
        if data.get('type') == 'Course':
            avg = data.get('average_package')
            fees = data.get('fees')
            # Only compute ROI if the course has an explicit source listed (branch CSV or reddit extraction)
            sources = data.get('sources') or []
            if sources and avg is not None and fees:
                try:
                    roi = float(avg) / float(fees) if fees else None
                except Exception:
                    roi = None
                data['roi'] = roi
                data['data_availability'] = 'available'
            else:
                data['average_package'] = None
                data['roi'] = None
                data['data_availability'] = 'insufficient'

    # persist graph as JSON-friendly dict
    # If no input files were present, optionally emit a minimal example graph so
    # the build script can produce a non-empty, inspectable knowledge snapshot.
    if G.number_of_nodes() == 0:
        msg = 'No raw input files found in data/raw/'
        if force_example:
            # emit a minimal example graph so the build script can produce a non-empty snapshot
            print('WARNING: Raw inputs missing — emitting example graph for debugging/demos.')
            # populate simple example
            G.add_node('college::RealCollege', type='College', name='RealCollege', aliases=['RealCollege'], fees=2.5)
            G.add_node('course::RealCollege::CS', type='Course', name='CS', college='RealCollege', average_package=9.5, fees=2.5, sources=["example:1"], roi=3.8, data_availability='available')
            G.add_edge('college::RealCollege', 'course::RealCollege::CS', type='offers_course')
        else:
            print('ERROR: No raw data found in data/raw/. Run ingestion scripts first, or provide raw files.')
            print(msg)
            raise SystemExit(2)

    os.makedirs(Path(out_path).parent, exist_ok=True)
    out = {'nodes': [], 'edges': []}
    for n, d in G.nodes(data=True):
        out['nodes'].append({'id': n, **d})
    for u, v, k, ed in G.edges(keys=True, data=True):
        out['edges'].append({'u': u, 'v': v, 'key': k, **ed})

    with open(out_path, 'w', encoding='utf8') as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)

    return out_path


def compute_roi(average_package, fees):
    """Compute ROI ratio safely (average_package in LPA, fees in Lakhs)."""
    try:
        if average_package is None or fees in (None, 0):
            return None
        return float(average_package) / float(fees)
    except Exception:
        return None



def load_graph(path=None):
    path = path or DATA_DIR / 'graph' / 'knowledge_graph.json'
    if not Path(path).exists():
        return None
    with open(path, encoding='utf8') as fh:
        return json.load(fh)


if __name__ == '__main__':
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument('--out', dest='out', help='Output path for knowledge_graph.json', default=None)
    p.add_argument('--force-example', dest='force_example', action='store_true', help='Emit an example graph even when raw inputs are missing')
    p.add_argument('--data-dir', dest='data_dir', help='Override data directory (for tests)', default=None)
    args = p.parse_args()

    print('building graph...')
    build_graph(out_path=args.out, force_example=args.force_example, data_dir=args.data_dir)
