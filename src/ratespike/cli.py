"""Command-line interface for ratespike."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .ratespike import detect, render_spikes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ratespike",
        description="Detect rate spikes in timestamped logs (offline, median/MAD).",
    )
    parser.add_argument("logfile", help="Path to a log file (or - for stdin)")
    parser.add_argument("--window", type=int, default=60, help="Bucket size in seconds (default 60)")
    parser.add_argument("--threshold", type=float, default=6.0,
                        help="Robust z-score needed to flag a spike (default 6.0)")
    parser.add_argument("--min-windows", type=int, default=5,
                        help="Prior windows needed for a baseline (default 5)")
    args = parser.parse_args(argv)

    if args.logfile == "-":
        lines = sys.stdin.read().splitlines()
    else:
        lines = Path(args.logfile).read_text(encoding="utf-8", errors="ignore").splitlines()

    spikes = detect(
        lines, window_seconds=args.window, threshold=args.threshold,
        min_windows=args.min_windows,
    )
    print(render_spikes(spikes))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
