import argparse
import json
import sys
from pathlib import Path

from src.reasoning import engine


def main(argv=None):
    parser = argparse.ArgumentParser(description="College knowledge CLI")
    sub = parser.add_subparsers(dest="cmd")

    p_rank = sub.add_parser("rank")
    p_rank.add_argument("--exam")
    p_rank.add_argument("--rank", type=int)
    p_rank.add_argument("--category")
    p_rank.add_argument("--preferred_courses", nargs="*", default=[])
    p_rank.add_argument("--no-cache", action="store_true")
    p_rank.add_argument("--render", action="store_true", help="Also print human-readable excerpts")

    p_sit = sub.add_parser("situation")
    p_sit.add_argument("--text")
    p_sit.add_argument("--no-cache", action="store_true")
    p_sit.add_argument("--render", action="store_true", help="Also print human-readable excerpts")

    args = parser.parse_args(argv)

    data_dir = Path(__file__).resolve().parents[1] / "data"
    graph_file = data_dir / "graph" / "knowledge_graph.json"

    if args.cmd == "rank":
        # basic sanitization for rank
        try:
            r = int(args.rank)
        except Exception:
            print('Error: --rank must be an integer (1..1000000)')
            sys.exit(2)
        if r <= 0 or r > 1_000_000:
            print('Error: --rank must be between 1 and 1,000,000')
            sys.exit(2)
        result = engine.answer(
            query_type="rank",
            exam=args.exam,
            rank=r,
            category=args.category,
            preferred_courses=args.preferred_courses,
            use_cache=not args.no_cache,
        )
    elif args.cmd == "situation":
        # sanitize free-text length
        text = (args.text or '').strip()
        if not text:
            print('Error: --text is required for situation queries')
            sys.exit(2)
        if len(text) > 2000:
            print('Error: --text too long (max 2000 chars)')
            sys.exit(2)
        result = engine.answer(
            query_type="situation",
            text=text,
            use_cache=not args.no_cache,
        )
    else:
        parser.print_help()
        sys.exit(2)

    print(json.dumps(result, indent=2, ensure_ascii=False))

    # Optionally print a human-friendly render with excerpts
    try:
        if getattr(args, 'render', False):
            from src.graph.build_graph import load_graph
            graph = load_graph(graph_file)
            rendered = engine.render_with_excerpts(result, graph)
            print('\n--- Human-readable render ---\n')
            print(rendered)
    except Exception:
        # Don't fail the CLI if rendering fails; JSON already printed
        pass


if __name__ == "__main__":
    main()
