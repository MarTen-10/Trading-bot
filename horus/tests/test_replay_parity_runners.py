import hashlib
from pathlib import Path

from horus.runners.backtest import run


def test_replay_parity_via_backtest_runner():
    csv_path = Path('/home/marten/.openclaw/workspace/horus/data/raw/crypto/BTCUSD_5m.csv')
    if not csv_path.exists():
        return
    a = run(str(csv_path))
    b = run(str(csv_path))
    ha = hashlib.sha256('|'.join(x.intent_id for x in a).encode()).hexdigest()
    hb = hashlib.sha256('|'.join(x.intent_id for x in b).encode()).hexdigest()
    assert ha == hb
