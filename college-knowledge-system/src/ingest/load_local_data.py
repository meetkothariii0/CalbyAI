"""Load local Arctic Shift export files and normalize to reddit_raw.jsonl schema.

- Finds *-posts.json and *-comments.json pairs under data/raw/
- Prints top-level keys/structure for one posts file and one comments file
- Normalizes records to: id,parent_id,body,score,num_replies,created_utc,subreddit,permalink
- Writes combined output to data/raw/reddit_raw.jsonl (replacing existing)
- Prints total record count and 3 sample records

Run: python -m src.ingest.load_local_data
"""
import json
import sys
from pathlib import Path
import hashlib

DATA_DIR = Path(__file__).resolve().parents[2] / 'data'
RAW_DIR = DATA_DIR / 'raw'
OUT_FILE = RAW_DIR / 'reddit_raw.jsonl'


def load_json_flex(path: Path):
    text = path.read_text(encoding='utf8')
    try:
        obj = json.loads(text)
        # If it's a dict at top-level, heuristically wrap in list if it contains items
        if isinstance(obj, dict):
            # if dict contains a "data" or "children" key with list, extract
            if 'data' in obj and isinstance(obj['data'], list):
                return obj['data']
            # if it's a mapping of id->obj, take values
            if all(isinstance(v, dict) for v in obj.values()):
                return list(obj.values())
            return [obj]
        return obj
    except json.JSONDecodeError:
        # try JSON lines
        items = []
        for ln in text.splitlines():
            ln = ln.strip()
            if not ln:
                continue
            try:
                items.append(json.loads(ln))
            except Exception:
                # skip unparsable lines
                continue
        return items


def sample_keys(items):
    if not items:
        return None
    it = items[0]
    if isinstance(it, dict):
        return list(it.keys())
    return type(it).__name__


def normalize_record(obj, default_subreddit=None):
    # id
    rid = obj.get('id') or obj.get('name')
    if not rid:
        # fallback stable hash
        rid = hashlib.md5(json.dumps(obj, sort_keys=True).encode('utf8')).hexdigest()[:12]
    # parent
    parent = obj.get('parent_id') or obj.get('parent') or None
    # body/selftext/title
    body = obj.get('body') or obj.get('selftext') or obj.get('self_text') or obj.get('title') or ''
    # score / ups
    score = obj.get('score') if 'score' in obj else obj.get('ups') if 'ups' in obj else obj.get('like_count') if 'like_count' in obj else None
    # num_replies or num_comments
    num_replies = obj.get('num_replies') if 'num_replies' in obj else obj.get('num_comments') if 'num_comments' in obj else None
    # created
    created = obj.get('created_utc') or obj.get('created') or obj.get('created_at') or None
    # subreddit/permalink/url
    subreddit = obj.get('subreddit') or default_subreddit
    permalink = obj.get('permalink') or obj.get('url') or None
    return {
        'id': rid,
        'parent_id': parent,
        'body': body,
        'score': score,
        'num_replies': num_replies,
        'created_utc': created,
        'subreddit': subreddit,
        'permalink': permalink
    }


def extract_college_from_filename(stem: str):
    # stem examples: '1-rvce-posts' or 'Acharya-comments' -> remove trailing '-posts'/'-comments' handled earlier
    # here stem is prefix like '1-rvce' or 'Acharya'
    if '-' in stem:
        parts = stem.split('-', 1)[1]
    else:
        parts = stem
    # normalize to uppercase token (e.g., rvce -> RVCE)
    return parts.replace('_', ' ').strip().upper()


def main():
    if not RAW_DIR.exists():
        print('No data/raw/ directory found at', RAW_DIR)
        sys.exit(1)

    posts = list(RAW_DIR.glob('*-posts.json'))
    comments = list(RAW_DIR.glob('*-comments.json'))

    if not posts and not comments:
        print('No *-posts.json or *-comments.json files found under', RAW_DIR)
        sys.exit(1)

    # Print top-level keys for one posts file and one comments file (if present)
    if posts:
        sample_posts = load_json_flex(posts[0])
        print('Sample posts file:', posts[0].name)
        print('Top-level keys (first item):', sample_keys(sample_posts))
    if comments:
        sample_comments = load_json_flex(comments[0])
        print('Sample comments file:', comments[0].name)
        print('Top-level keys (first item):', sample_keys(sample_comments))

    combined = []
    # process posts
    for p in posts:
        items = load_json_flex(p)
        # determine default subreddit from filename
        stem = p.stem[:-6] if p.stem.endswith('-posts') else p.stem
        default_sub = extract_college_from_filename(stem)
        for obj in items:
            nr = normalize_record(obj, default_subreddit=default_sub)
            combined.append(nr)

    # process comments
    for c in comments:
        items = load_json_flex(c)
        stem = c.stem[:-9] if c.stem.endswith('-comments') else c.stem
        default_sub = extract_college_from_filename(stem)
        for obj in items:
            nr = normalize_record(obj, default_subreddit=default_sub)
            combined.append(nr)

    # write combined to reddit_raw.jsonl (replace)
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, 'w', encoding='utf8') as fh:
        for rec in combined:
            fh.write(json.dumps(rec, ensure_ascii=False) + '\n')

    print('Wrote', len(combined), 'records to', OUT_FILE)
    # print 3 samples with body
    samples = [r for r in combined if r.get('body')]
    for i, s in enumerate(samples[:3]):
        print('\n--- sample', i+1, '---')
        print(json.dumps(s, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
