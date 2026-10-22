from ratespike.ratespike import (
    bucket_lines,
    detect,
    detect_spikes,
    mad,
    median,
    parse_timestamp,
    render_spikes,
)


def _lines(counts_per_minute):
    """Build log lines with a given number of events in consecutive minutes."""
    lines = []
    for minute, count in enumerate(counts_per_minute):
        for _ in range(count):
            lines.append(f"2026-10-29T00:{minute:02d}:00Z event happened")
    return lines


def test_parse_timestamp_iso_and_z():
    ts = parse_timestamp("2026-10-29T12:34:56Z something")
    assert ts is not None and ts.year == 2026
    assert parse_timestamp("no timestamp here") is None


def test_parse_timestamp_space_separator_and_offset():
    ts = parse_timestamp("2026-10-29 12:34:56+02:00 app")
    assert ts is not None
    # 12:34:56+02:00 == 10:34:56 UTC
    assert ts.hour == 10


def test_bucket_counts():
    counts = bucket_lines(_lines([2, 0, 3]), window_seconds=60)
    assert sorted(counts.values()) == [0, 2, 3] or sorted(counts.values()) == [2, 3]


def test_median_and_mad():
    assert median([1, 3, 5]) == 3
    assert median([1, 2, 3, 4]) == 2.5
    assert mad([1, 3, 5], center=3) == 2
    assert mad([]) == 0.0


def test_spike_detected():
    # Steady baseline of 2, then a burst of 50.
    counts = {i * 60: c for i, c in enumerate([2, 2, 2, 2, 2, 2, 50])}
    spikes = detect_spikes(counts, threshold=6.0, min_windows=5)
    assert len(spikes) == 1
    assert spikes[0].count == 50
    assert spikes[0].baseline == 2.0


def test_no_spike_on_steady_traffic():
    counts = {i * 60: 5 for i in range(10)}
    assert detect_spikes(counts, threshold=6.0) == []


def test_baseline_needs_enough_windows():
    counts = {i * 60: 2 for i in range(3)}  # fewer than min_windows
    assert detect_spikes(counts, min_windows=5) == []


def test_zero_spread_baseline_flags_increase():
    # Flat baseline (MAD=0) then a jump: count above median is a spike.
    counts = {i * 60: 1 for i in range(6)}
    counts[6 * 60] = 20
    spikes = detect_spikes(counts, threshold=6.0, min_windows=5)
    assert len(spikes) == 1 and spikes[0].count == 20


def test_detect_from_lines_and_render():
    spikes = detect(_lines([2, 2, 2, 2, 2, 2, 60]), threshold=6.0)
    assert len(spikes) == 1
    text = render_spikes(spikes)
    assert "spike(s) detected" in text
    assert "count=60" in text


def test_render_no_spikes():
    assert render_spikes([]) == "No spikes detected."
