#!/usr/bin/env python3
import hashlib, json, os
from dataclasses import dataclass
from pathlib import Path

CAL = Path('/home/marten/.openclaw/workspace/horus/data/reports/calibration_report_latest.json')


@dataclass
class Fill:
    order_id: str
    fill_px: float
    fill_qty: float
    slippage_bps: float


def _p75_slippage(instrument: str) -> float:
    percentile = os.getenv('HORUS_SLIPPAGE_PERCENTILE', 'p75')
    if not CAL.exists():
        return 3.0
    j = json.loads(CAL.read_text())
    s = j.get('instrument_summary', {}).get(instrument)
    if not s:
        return 3.0
    return float(s.get(percentile, s.get('p75', 3.0)))


def _det_id(*parts):
    x = '|'.join(str(p) for p in parts)
    return hashlib.sha256(x.encode()).hexdigest()[:32]


def place_order(intent) -> tuple[dict, Fill]:
    # deterministic fill model using calibrated p75 slippage
    from horus.core.events import OrderIntent
    if not isinstance(intent, OrderIntent):
        raise TypeError('Execution adapter accepts only OrderIntent from Engine.process_event')

    instrument = intent.instrument
    side = intent.side
    px = float(intent.entry_px)
    qty = float(intent.qty)
    sl_bps = _p75_slippage(instrument)
    fee_bps = 1.0

    bps = (sl_bps + fee_bps) / 10000.0
    fill_px = px * (1 + bps) if side == 'buy' else px * (1 - bps)

    order_id = _det_id('order', intent.intent_type, intent.intent_id, intent.signal_id, intent.event_ts)
    fill_id = _det_id('fill', order_id)

    from horus.runtime import dbio

    def _write(con):
        with con.cursor() as cur:
            # Invariant guard: ensure parent signal row exists before orders FK insert.
            cur.execute(
                """
                INSERT INTO signals(signal_id, timestamp, instrument, strategy, decision, veto_reason)
                VALUES(%s,%s,%s,%s,%s,%s)
                ON CONFLICT(signal_id) DO NOTHING
                """,
                (intent.signal_id, intent.event_ts, intent.instrument, 'breakout_v2', 'taken', ''),
            )
            cur.execute(
                "INSERT INTO orders(order_id, signal_id, status, sent_at, ack_at) VALUES(%s,%s,%s,%s,%s) ON CONFLICT(order_id) DO UPDATE SET status=EXCLUDED.status,sent_at=EXCLUDED.sent_at,ack_at=EXCLUDED.ack_at",
                (order_id, intent.signal_id, 'filled', intent.event_ts, intent.event_ts)
            )
            cur.execute(
                "INSERT INTO fills(fill_id, order_id, timestamp, fill_px, fill_qty, mid_at_send, bid_at_send, ask_at_send, slippage_bps) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(fill_id) DO UPDATE SET fill_px=EXCLUDED.fill_px,fill_qty=EXCLUDED.fill_qty,slippage_bps=EXCLUDED.slippage_bps",
                (fill_id, order_id, intent.event_ts, fill_px, qty, px, px, px, sl_bps)
            )
    dbio.with_conn(_write)

    fill = Fill(order_id=order_id, fill_px=fill_px, fill_qty=qty, slippage_bps=sl_bps)
    return ({'order_id': order_id, 'status': 'filled', 'intent_type': intent.intent_type}, fill)
