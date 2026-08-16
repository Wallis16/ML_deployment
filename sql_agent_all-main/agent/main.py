import argparse
import sys

from .graph import build_graph

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> None:
    parser = argparse.ArgumentParser(description="SQL agent over the movie_lens and olist databases")
    parser.add_argument("question", help="A natural-language question to answer with SQL")
    parser.add_argument("--max-attempts", type=int, default=3, help="Max run_sql retries")
    args = parser.parse_args()

    app = build_graph()
    result = app.invoke({"question": args.question, "max_attempts": args.max_attempts})

    print(f"\nDatabase: {result.get('database')}")
    print(f"SQL:\n{result.get('query')}\n")
    print("Report:")
    print(result.get("report", "(no report produced)"))
    if result.get("plot_path"):
        print(f"\nPlot saved to: {result['plot_path']}")


if __name__ == "__main__":
    sys.exit(main() or 0)
