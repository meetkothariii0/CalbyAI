import json
import subprocess
import sys
import unittest
from pathlib import Path
import tempfile


REPO = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = REPO / 'src' / 'graph' / 'build_graph.py'


def run_build(args=None, data_dir=None):
    cmd = [sys.executable, str(BUILD_SCRIPT)]
    if args:
        cmd += args
    if data_dir:
        cmd += ['--data-dir', str(data_dir)]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    out, _ = p.communicate()
    return p.returncode, out


class StrictBuildTests(unittest.TestCase):
    def test_build_strict_fails_on_empty_raw(self):
        with tempfile.TemporaryDirectory() as td:
            data_root = Path(td)
            # ensure empty raw exists under data/ to match repo layout
            (data_root / 'data' / 'raw').mkdir(parents=True, exist_ok=True)
            graph_file = data_root / 'data' / 'graph' / 'knowledge_graph.json'
            if graph_file.exists():
                graph_file.unlink()
            code, out = run_build(data_dir=data_root)
            self.assertNotEqual(code, 0)
            self.assertIn('No raw input files found', out)

    def test_build_force_example_succeeds_and_warns(self):
        with tempfile.TemporaryDirectory() as td:
            data_root = Path(td)
            (data_root / 'data' / 'raw').mkdir(parents=True, exist_ok=True)
            graph_file = data_root / 'data' / 'graph' / 'knowledge_graph.json'
            if graph_file.exists():
                graph_file.unlink()
            code, out = run_build(['--force-example'], data_dir=data_root)
            self.assertEqual(code, 0)
            self.assertTrue('WARNING' in out.upper() or 'example' in out.lower())
            self.assertTrue(graph_file.exists())

    def test_build_with_real_data(self):
        with tempfile.TemporaryDirectory() as td:
            data_root = Path(td)
            raw = data_root / 'data' / 'raw'
            raw.mkdir(parents=True, exist_ok=True)
            # write branch_packages.csv
            with open(raw / 'branch_packages.csv', 'w', encoding='utf8') as fh:
                fh.write('college,course,average_package_lpa,fees_lakhs\n')
                fh.write('RealCollege,CS,9.5,2.5\n')
            # write reddit_raw.jsonl
            with open(raw / 'reddit_raw.jsonl', 'w', encoding='utf8') as fh:
                fh.write('{"id":"r1","body":"Good placements at RealCollege","score":10,"subreddit":"RealCollege","created_utc":1600000000}\n')

            graph_file = data_root / 'data' / 'graph' / 'knowledge_graph.json'
            if graph_file.exists():
                graph_file.unlink()
            code, out = run_build(data_dir=data_root)
            self.assertEqual(code, 0)
            self.assertTrue(graph_file.exists())
            g = json.loads(graph_file.read_text(encoding='utf8'))
            # find Course node for RealCollege
            courses = [n for n in g.get('nodes', []) if n.get('type') == 'Course' and n.get('college') == 'RealCollege']
            self.assertTrue(len(courses) >= 1)
            c = courses[0]
            # average_package may be numeric or stored as string; normalize
            self.assertTrue(float(c.get('average_package') or 0) == 9.5)


if __name__ == '__main__':
    unittest.main()
