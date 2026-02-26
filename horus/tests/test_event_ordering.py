import csv
from pathlib import Path

from horus.runners.backtest import run


def _write(path: Path, rows):
    with path.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'instrument'])
        w.writeheader()
        w.writerows(rows)


def test_unsorted_input_yields_same_outputs(tmp_path: Path):
    rows = [
        {'timestamp': '2026-01-01T00:10:00Z', 'open': 1, 'high': 2, 'low': 0.5, 'close': 1.5, 'volume': 10, 'instrument': 'BTCUSD'},
        {'timestamp': '2026-01-01T00:00:00Z', 'open': 1, 'high': 2, 'low': 0.5, 'close': 1.5, 'volume': 10, 'instrument': 'BTCUSD'},
        {'timestamp': '2026-01-01T00:05:00Z', 'open': 1, 'high': 2, 'low': 0.5, 'close': 1.5, 'volume': 10, 'instrument': 'BTCUSD'},
    ]
    a = tmp_path / 'a.csv'
    b = tmp_path / 'b.csv'
    _write(a, rows)
    _write(b, list(reversed(rows)))

    out_a = [x.intent_id for x in run(str(a))]
    out_b = [x.intent_id for x in run(str(b))]
    assert out_a == out_b
