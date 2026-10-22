"""Offline log-event rate anomaly detection.

Reads timestamped log lines, buckets them into fixed windows, and flags windows
whose event rate is anomalously high compared to a rolling baseline. The
baseline is robust: it uses the median and MAD (median absolute deviation), so a
sustained spike does not immediately drag the baseline up and hide itself.

No dependencies, no network — just the standard library.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone

# ISO-8601-ish timestamps, with optional fractional seconds and zone.
_TS_RE = re.compile(
    r"(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)"
)


def parse_timestamp(line: str) -> datetime | None:
    """Extract the first ISO-8601 timestamp from a log line, or None."""
    m = _TS_RE.search(line)
    if not m:
        return None
    raw = m.group(1).replace(" ", "T", 1)
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def bucket_lines(lines, window_seconds: int = 60) -> dict[int, int]:
    """Count events per fixed window (keyed by window start epoch seconds)."""
    counts: dict[int, int] = {}
    for line in lines:
        ts = parse_timestamp(line)
        if ts is None:
            continue
        start = int(ts.timestamp()) // window_seconds * window_seconds
        counts[start] = counts.get(start, 0) + 1
    return counts


def median(values: list[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    mid = n // 2
    if n % 2:
        return float(s[mid])
    return (s[mid - 1] + s[mid]) / 2.0


def mad(values: list[float], center: float | None = None) -> float:
    """Median absolute deviation (raw, not scaled)."""
    if not values:
        return 0.0
    c = median(values) if center is None else center
    return median([abs(v - c) for v in values])


@dataclass
class Spike:
    window_start: int
    count: int
    baseline: float
    score: float  # robust z-score (MAD-based)


def detect_spikes(
    counts: dict[int, int],
    window_seconds: int = 60,
    threshold: float = 6.0,
    min_windows: int = 5,
    guard_windows: int = 1,
) -> list[Spike]:
    """Flag windows whose rate is anomalously high vs a rolling robust baseline.

    For each window, the baseline is the median count of the preceding
    ``min_windows`` windows (excluding the current and the immediately preceding
    ``guard_windows`` so a spike does not contaminate its own baseline). The
    score is a MAD-based robust z-score; windows at or above ``threshold`` are
    reported as spikes.

    Requires at least ``min_windows`` prior windows; otherwise returns [].
    """
    if not counts:
        return []
    starts = sorted(counts)
    spikes: list[Spike] = []
    for i, start in enumerate(starts):
        # Collect baseline counts from earlier windows only.
        prior = [counts[s] for s in starts[: i - guard_windows]]
        if len(prior) < min_windows:
            continue
        recent = prior[-min_windows:]
        center = median(recent)
        deviation = mad(recent, center)
        count = counts[start]
        if deviation == 0:
            # No spread in the baseline: any increase over the median is a spike
            # only if it is strictly greater (and non-trivial).
            score = float(count - center) if count > center else 0.0
        else:
            # 1.4826 scales MAD to be comparable to standard deviation.
            score = (count - center) / (1.4826 * deviation)
        if score >= threshold and count > center:
            spikes.append(Spike(start, count, center, score))
    return spikes


def detect(lines, window_seconds: int = 60, threshold: float = 6.0, **kw) -> list[Spike]:
    """Convenience: bucket raw log lines then detect spikes."""
    counts = bucket_lines(lines, window_seconds)
    return detect_spikes(counts, window_seconds, threshold, **kw)


def render_spikes(spikes: list[Spike]) -> str:
    if not spikes:
        return "No spikes detected."
    lines = [f"{len(spikes)} spike(s) detected:"]
    for s in spikes:
        ts = datetime.fromtimestamp(s.window_start, tz=timezone.utc).isoformat()
        lines.append(
            f"  {ts}  count={s.count}  baseline={s.baseline:.1f}  score={s.score:.1f}"
        )
    return "\n".join(lines)
