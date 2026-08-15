"""Turns a Locust --csv run into a plain-text summary and a PNG chart.

Usage:
    python summarize.py <results_dir>

Expects <results_dir>/stats_stats.csv, stats_stats_history.csv, and
stats_failures.csv (i.e. run_load_test.sh's --csv "$OUT_DIR/stats" prefix).
Writes summary.txt and summary.png into the same directory.
"""

import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def summarize(results_dir: Path) -> None:
    stats = pd.read_csv(results_dir / "stats_stats.csv")
    history = pd.read_csv(results_dir / "stats_stats_history.csv")
    failures_path = results_dir / "stats_failures.csv"
    failures = pd.read_csv(failures_path) if failures_path.exists() and failures_path.stat().st_size > 0 else None

    # History rows carry "N/A" for percentile columns in periods with zero
    # requests — coerce those to NaN so the numeric columns actually plot.
    numeric_cols = ["Requests/s", "Failures/s", "50%", "95%", "99%", "User Count"]
    for col in numeric_cols:
        history[col] = pd.to_numeric(history[col], errors="coerce")
    history["Elapsed (s)"] = history["Timestamp"] - history["Timestamp"].iloc[0]

    agg = stats[stats["Name"] == "Aggregated"].iloc[0]
    per_endpoint = stats[stats["Name"] != "Aggregated"]

    lines = [
        "SQL Agent — Load Test Summary",
        "=" * 32,
        "",
        f"Total requests:     {int(agg['Request Count'])}",
        f"Failed requests:    {int(agg['Failure Count'])} ({agg['Failure Count'] / max(agg['Request Count'], 1):.1%})",
        f"Throughput:         {agg['Requests/s']:.2f} req/s",
        f"Peak concurrent users: {int(history['User Count'].max())}",
        "",
        "Response times (ms), aggregated:",
        f"  min    {agg['Min Response Time']:.0f}",
        f"  median {agg['Median Response Time']:.0f}",
        f"  avg    {agg['Average Response Time']:.0f}",
        f"  p95    {agg['95%']:.0f}",
        f"  p99    {agg['99%']:.0f}",
        f"  max    {agg['Max Response Time']:.0f}",
        "",
        "By endpoint:",
    ]
    for _, row in per_endpoint.iterrows():
        lines.append(
            f"  {row['Type']:<5} {row['Name']:<10} "
            f"n={int(row['Request Count']):<6} fail={int(row['Failure Count']):<4} "
            f"median={row['Median Response Time']:.0f}ms p95={row['95%']:.0f}ms p99={row['99%']:.0f}ms "
            f"{row['Requests/s']:.2f} req/s"
        )

    if failures is not None:
        lines += ["", "Failures:"]
        for _, row in failures.iterrows():
            lines.append(f"  [{row['Method']} {row['Name']}] {row['Error']}  (x{row['Occurrences']})")
    else:
        lines += ["", "Failures: none"]

    (results_dir / "summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))

    fig, (ax_rps, ax_latency) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

    ax_rps.plot(history["Elapsed (s)"], history["Requests/s"], label="Requests/s", color="tab:blue")
    ax_rps.plot(history["Elapsed (s)"], history["Failures/s"], label="Failures/s", color="tab:red")
    ax_rps_users = ax_rps.twinx()
    ax_rps_users.plot(history["Elapsed (s)"], history["User Count"], label="Users", color="tab:gray", linestyle="--")
    ax_rps.set_ylabel("req/s")
    ax_rps_users.set_ylabel("concurrent users")
    ax_rps.set_title("Throughput and concurrent users over time")
    lines1, labels1 = ax_rps.get_legend_handles_labels()
    lines2, labels2 = ax_rps_users.get_legend_handles_labels()
    ax_rps.legend(lines1 + lines2, labels1 + labels2, loc="upper left")

    ax_latency.plot(history["Elapsed (s)"], history["50%"], label="p50")
    ax_latency.plot(history["Elapsed (s)"], history["95%"], label="p95")
    ax_latency.plot(history["Elapsed (s)"], history["99%"], label="p99")
    ax_latency.set_ylabel("response time (ms)")
    ax_latency.set_xlabel("elapsed (s)")
    ax_latency.set_title("Response time percentiles over time")
    ax_latency.legend(loc="upper left")

    fig.suptitle(f"Load test — {int(agg['Request Count'])} requests, {agg['Failure Count'] / max(agg['Request Count'], 1):.1%} failed")
    fig.tight_layout()
    fig.savefig(results_dir / "summary.png", dpi=150)
    print(f"\nWrote {results_dir / 'summary.txt'} and {results_dir / 'summary.png'}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python summarize.py <results_dir>")
        sys.exit(1)
    summarize(Path(sys.argv[1]))
