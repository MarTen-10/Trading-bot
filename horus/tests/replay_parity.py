#!/usr/bin/env python3
import csv, hashlib, json, sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '/home/marten/.openclaw/workspace')

from horus.runtime.event_bus import BUS, MarketEvent
from horus.runtime.strategy import StrategyEngine
from horus.runtime.risk_engine import RiskEngine
from horus.runtime.paper_execution import place_order
from horus.runtime import gate_adapter
from horus.core.events import OrderIntent

BASE = Path('/home/marten/.openclaw/workspace/horus')


def prep_gate_and_regime():
    (BASE/'data/reports').mkdir(parents=True, exist_ok=True)
    (BASE/'data/reports/runtime_gate_latest.json').write_text(json.dumps({
        'promotion_status': 'PROMOTE',
        'disable_status': 'KEEP',
        'rolling_expectancy': {'latest': 0.2}
    }))
    (BASE/'data/reports/regime_labels_btc_latest.json').write_text(json.dumps({
        'labels': [{'regime': 'TREND_NORMAL'}]
    }))


def load_events(csv_path, max_rows=12):
    rows = []
    with open(csv_path, newline='') as f:
        r = csv.DictReader(f)
        for i, row in enumerate(r):
            if i >= max_rows:
                break
            rows.append(row)
    return rows


def replay_once(csv_path):
    BUS._q.clear()  # deterministic test reset
    BUS._seq.clear()
    strat = StrategyEngine()
    risk = RiskEngine(0.01, -3)

    signals, orders, trades = [], [], []
    for row in load_events(csv_path):
        ts = datetime.fromisoformat(row['timestamp'].replace('Z','+00:00'))
        seq = BUS.next_sequence('BTCUSD', '5m')
        ev = MarketEvent('BTCUSD', '5m', ts, float(row['open']), float(row['high']), float(row['low']), float(row['close']), float(row.get('volume',0) or 0), seq)
        BUS.emit(ev)

        event = BUS.next()
        sig = strat.generate(event)
        if not sig:
            continue
        allowed, _, _ = gate_adapter.allow(sig)
        if not allowed:
            continue
        ok, _ = risk.allow(sig)
        if not ok:
            continue
        qty, risk_d = risk.size(sig, equity=1000.0)
        intent = OrderIntent(
            intent_id='test_intent',
            signal_id=sig['signal_id'],
            instrument=sig['instrument'],
            side=sig['side'],
            entry_px=float(sig['entry_px']),
            stop_px=float(sig['stop_px']),
            qty=float(qty),
            risk_dollars=float(risk_d),
            event_ts=sig['ts'],
        )
        order, fill = place_order(intent)

        trade_obj = {
            'signal_id': sig['signal_id'],
            'order_id': order['order_id'],
            'fill_px': round(fill.fill_px, 8),
            'qty': round(fill.fill_qty, 8)
        }
        signals.append(sig['signal_id'])
        orders.append(order['order_id'])
        trades.append(trade_obj)

    sig_hash = hashlib.sha256('|'.join(signals).encode()).hexdigest()
    ord_hash = hashlib.sha256('|'.join(orders).encode()).hexdigest()
    tr_hash = hashlib.sha256('|'.join(f"{t['signal_id']}:{t['order_id']}:{t['fill_px']}:{t['qty']}" for t in trades).encode()).hexdigest()
    return {'signals': signals, 'orders': orders, 'trades': trades, 'signal_hash': sig_hash, 'order_hash': ord_hash, 'trade_hash': tr_hash}


def main():
    prep_gate_and_regime()
    csv_files = sorted((BASE/'data'/'raw'/'crypto').glob('BTCUSD_5m.csv'))
    if not csv_files:
        raise SystemExit('missing BTCUSD_5m.csv for parity test')
    csv_path = str(csv_files[-1])

    a = replay_once(csv_path)
    b = replay_once(csv_path)

    assert a['signal_hash'] == b['signal_hash'], 'signal_hash_mismatch'
    assert a['order_hash'] == b['order_hash'], 'order_hash_mismatch'
    assert a['trade_hash'] == b['trade_hash'], 'trade_hash_mismatch'
    print('REPLAY_PARITY_OK')


if __name__ == '__main__':
    main()
