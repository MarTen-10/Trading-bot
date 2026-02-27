from datetime import datetime, UTC

import pytest

from horus.core.engine import Engine
from horus.core.events import CandleEvent
from horus.runtime.paper_execution import place_order


class S:
    def __init__(self):
        self.i = 0

    def generate(self, event):
        self.i += 1
        return {
            'signal_id': f's{self.i}',
            'instrument': event.instrument,
            'ts': event.timestamp.isoformat(),
            'side': 'buy',
            'entry_px': event.close,
            'stop_px': event.close * 0.99,
        }


class R:
    def allow(self, signal):
        return True, None

    def size(self, signal, equity=1000.0):
        return 1.0, 10.0


class G:
    def allow(self, signal):
        return True, None, {'regime': 'TREND_NORMAL'}


class DB:
    def __init__(self):
        self.events = []

    def insert_governance(self, *args):
        self.events.append(args)


def ev(instr='BTCUSD', seq=1):
    return CandleEvent(instr, '5m', datetime(2026, 1, 1, tzinfo=UTC), 1, 2, 0.5, 1.5, 10, seq)


def test_max_open_exposure_2r_blocks_third_entry():
    db = DB()
    e = Engine(strategy=S(), risk=R(), gate=G(), dbio=db, logger=lambda *a, **k: None)
    d1 = e.process_event(ev('BTCUSD', 1))
    d2 = e.process_event(ev('ETHUSD', 2))
    d3 = e.process_event(ev('SOLUSD', 3))
    assert len(d1.intents) == 1
    assert len(d2.intents) == 1
    assert len(d3.intents) == 0
    assert d3.veto_reason == 'RISK_EXPOSURE_CAP'
    assert any(x[0] == 'RISK_EXPOSURE_CAP' for x in db.events)


def test_safe_mode_hard_gate_zero_order_intents():
    db = DB()
    e = Engine(strategy=S(), risk=R(), gate=G(), dbio=db, logger=lambda *a, **k: None)
    e.state.safe_mode = True
    d = e.process_event(ev('BTCUSD', 1))
    assert d.signal is not None
    assert len(d.intents) == 0
    assert d.veto_reason == 'SAFE_MODE_ACTIVE'
    assert any(x[0] == 'SAFE_BLOCK_ENTRY' for x in db.events)


def test_direct_execution_bypass_blocked():
    with pytest.raises(TypeError):
        place_order({'signal_id': 'x'})
