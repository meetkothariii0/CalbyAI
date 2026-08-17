import tempfile, subprocess, sys
from pathlib import Path

td = Path(tempfile.mkdtemp())
print('tmpdir:', td)
raw = td / 'data' / 'raw'
raw.mkdir(parents=True)
with open(raw / 'branch_packages.csv', 'w', encoding='utf8') as fh:
    fh.write('college,course,average_package_lpa,fees_lakhs\n')
    fh.write('RealCollege,CS,9.5,2.5\n')
with open(raw / 'reddit_raw.jsonl', 'w', encoding='utf8') as fh:
    fh.write('{"id":"r1","body":"Good placements at RealCollege","score":10,"subreddit":"RealCollege","created_utc":1600000000}\n')
cmd = [sys.executable, str(Path(__file__).resolve().parents[1] / 'src' / 'graph' / 'build_graph.py'), '--data-dir', str(td)]
print('cmd:', cmd)
p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
out, _ = p.communicate()
print('rc=', p.returncode)
print(out)
print('graph exists?', (td / 'data' / 'graph' / 'knowledge_graph.json').exists())
