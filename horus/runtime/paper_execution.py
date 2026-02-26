#!/usr/bin/env python3
import hashlib, json
from dataclasses import dataclass
from pathlib import Path

from horus.runtime import dbio

CAL = Path('/home/marten/.openclaw/workspace/horus/data/reports/calibration_report_latest.json')

@dataclass
class Fill:
    order_id: str
    fill_px: float
    fill_qty: float
    slippage_bps: float


def _p75_slippage(instrument: str) -> float:
    if not CAL.exists():
        return 3.0
    j = json.loads(CAL.read_text())
    s = j.get('instrument_summary', {}).get(instrument)
    if not s:
        return 3.0
    return float(s.get('p75', 3.0))


def _det_id(*parts):
    x = '|'.join(str(p) for p in parts)
    return hashlib.sha256(x.encode()).hexdigest()[:32]


def place_order(signal: dict) -> tuple[dict, Fill]:
    # deterministic fill model using calibrated p75 slippage
    instrument = signal['instrument']
    side = signal['side']
    px = float(signal['entry_px'])
    qty = float(signal['qty'])
    sl_bps = _p75_slippage(instrument)
    fee_bps = 1.0

    # buy adds cost, sell subtracts
    bps = (sl_bps + fee_bps) / 10000.0
    fill_px = px * (1 + bps) if side == 'buy' else px * (1 - bps)

    order_id = _det_id('order', signal['signal_id'])
    fill_id = _det_id('fill', order_id)

    # DB writes (sqlite path)
    dbio.with_sqlite(lambda con: con.execute(
        "INSERT OR REPLACE INTO orders(order_id, signal_id, status, sent_at, ack_at) VALUES(?,?,?,?,?)",
        (order_id, signal['signal_id'], 'filled', signal['ts'], signal['ts'])
    ))
    dbio.with_sqlite(lambda con: con.execute(
        "INSERT OR REPLACE INTO fills(fill_id, order_id, ts, fill_px, fill_qty, mid_at_send, bid_at_send, ask_at_send, slippage_bps) VALUES(?,?,?,?,?,?,?,?,?)",
        (fill_id, order_id, signal['ts'], fill_px, qty, px, px, px, sl_bps)
    ))

    fill = Fill(order_id=order_id, fill_px=fill_px, fill_qty=qty, slippage_bps=sl_bps)
    return ({'order_id': order_id, 'status': 'filled'}, fill)
