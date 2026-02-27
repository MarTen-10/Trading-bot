from datetime import datetime, UTC, timedelta

import pytest

from horus.core.engine import Engine
from horus.core.events import CandleEvent
from horus.runtime.lifecycle import bootstrap_engine_from_db


class ScriptedStrategy:
    def __init__(self):
        self.sent = False

    def generate(self, event):
        if self.sent:
            return None
        self.sent = True
        return {
            'signal_id': 'sig-1',
            'instrument': event.instrument,
            'ts': event.timestamp.isoformat(),
            'side': 'buy',
            'entry_px': event.close,
            'stop_px': event.close * 0.99,
        }


class AllowRisk:
    def allow(self, signal):
        return True, None

    def size(self, signal, equity=1000.0):
        return 1.0, 10.0


class AllowGate:
    def allow(self, signal):
        return True, None, {'regime': 'VOL_SHOCK'}


class NullDB:
    def insert_governance(self, *args, **kwargs):
        return None


class FakeDB:
    def fetch_open_trades(self):
        return [{
            'trade_id': 't-open-1',
            'signal_id': 's-open-1',
            'instrument': 'BTCUSD',
            'side': 'buy',
            'entry_timestamp': datetime(2026, 1, 1, tzinfo=UTC),
            'entry_price': 100.0,
            'qty': 1.0,
            'risk_r': 1.0,
            'entry_sequence_id': 10,
            'stop_price': 99.0,
            'take_price': None,
        }]


def ev(seq: int, ts: datetime):
    return CandleEvent('BTCUSD', '5m', ts, 1, 2, 0.5, 1.5, 10, seq)


def test_position_persists_until_exit_rule_fires():
    e = Engine(strategy=ScriptedStrategy(), risk=AllowRisk(), gate=AllowGate(), dbio=NullDB(), logger=lambda *a, **k: None)
    e.state.exit_after_candles = 2

    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    d1 = e.process_event(ev(1, t0))
    assert len(d1.intents) == 1
    assert d1.intents[0].intent_type == 'ENTRY'
    e.on_entry_filled(d1.intents[0], event_sequence_id=1, entry_fill_px=1.5)
    assert e.state.open_exposure_r == 1.0

    d2 = e.process_event(ev(2, t0 + timedelta(minutes=5)))
    assert all(i.intent_type != 'EXIT' for i in d2.intents)
    assert e.state.open_exposure_r == 1.0

    d3 = e.process_event(ev(3, t0 + timedelta(minutes=10)))
    exits = [i for i in d3.intents if i.intent_type == 'EXIT']
    assert exits
    e.on_exit_filled(exits[0], exit_fill_px=1.6, exit_ts=(t0 + timedelta(minutes=10)).isoformat(), exit_reason='time_exit')
    assert e.state.open_exposure_r == 0.0


def test_exposure_increases_on_entry_and_decreases_on_exit():
    e = Engine(strategy=ScriptedStrategy(), risk=AllowRisk(), gate=AllowGate(), dbio=NullDB(), logger=lambda *a, **k: None)
    e.state.exit_after_candles = 1

    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    d1 = e.process_event(ev(1, t0))
    e.on_entry_filled(d1.intents[0], event_sequence_id=1, entry_fill_px=1.5)
    assert e.state.open_exposure_r == pytest.approx(1.0)

    d2 = e.process_event(ev(2, t0 + timedelta(minutes=5)))
    exits = [i for i in d2.intents if i.intent_type == 'EXIT']
    e.on_exit_filled(exits[0], exit_fill_px=1.4, exit_ts=(t0 + timedelta(minutes=5)).isoformat(), exit_reason='time_exit')
    assert e.state.open_exposure_r == pytest.approx(0.0)


def test_restart_reconstruction_from_db_rows():
    e = Engine(strategy=ScriptedStrategy(), risk=AllowRisk(), gate=AllowGate(), dbio=NullDB(), logger=lambda *a, **k: None)
    out = bootstrap_engine_from_db(e, FakeDB())
    assert out['open_positions'] == 1
    assert out['open_exposure_r'] == pytest.approx(1.0)
    assert e.state.open_exposure_r == pytest.approx(1.0)
    assert 'BTCUSD' in e.state.positions
