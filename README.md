# ratespike

Find rate spikes in timestamped logs — offline, no agents, no dependencies.
`ratespike` buckets log events into fixed windows and flags any window whose
rate is anomalously high compared to a **rolling robust baseline** (median +
MAD). Because the baseline is median-based rather than mean-based, a sustained
spike does not immediately drag the baseline up and hide itself.

## How it works

1. **Parse** the first ISO-8601 timestamp on each line (`...Z`, `...+02:00`, or a
   space separator). Lines without a timestamp are skipped.
2. **Bucket** events into fixed windows (default 60s).
3. For each window, compute a **robust z-score** against the median/MAD of the
   preceding `--min-windows` windows (excluding a guard window so a spike does
   not contaminate its own baseline).
4. **Flag** windows whose score is at or above `--threshold`.

When the baseline has zero spread (MAD = 0), any increase over the median is
treated as a spike.

## Install

```
pip install -e .
```

## Usage

```
ratespike app.log --window 60 --threshold 6.0
# or
cat app.log | ratespike - --threshold 8
```

Prints each spike with its window start (UTC), event count, baseline, and score.

## Python API

```python
from ratespike import detect, render_spikes

spikes = detect(open("app.log"), window_seconds=60, threshold=6.0)
print(render_spikes(spikes))
```

## License

MIT
