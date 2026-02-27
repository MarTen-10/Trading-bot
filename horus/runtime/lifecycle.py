#!/usr/bin/env python3
from horus.core.engine import Position


def bootstrap_engine_from_db(engine, dbio):
    """Rebuild in-memory lifecycle state from DB OPEN trades."""
    positions = {}
    total_r = 0.0

    rows = dbio.fetch_open_trades() if hasattr(dbio, 'fetch_open_trades') else []
    for r in rows or []:
        instrument = r.get('instrument')
        if not instrument:
            continue
        risk_r = float(r.get('risk_r') or 1.0)
        p = Position(
            position_id=r.get('trade_id') or r.get('signal_id') or instrument,
            signal_id=r.get('signal_id') or r.get('trade_id') or instrument,
            instrument=instrument,
            side=r.get('side') or 'buy',
            entry_ts=(r.get('entry_timestamp').isoformat() if hasattr(r.get('entry_timestamp'), 'isoformat') else str(r.get('entry_timestamp'))),
            entry_sequence_id=int(r.get('entry_sequence_id') or 0),
            entry_price=float(r.get('entry_price') or 0.0),
            risk_r=risk_r,
            qty=float(r.get('qty') or 0.0),
            stop_price=float(r.get('stop_price') or 0.0),
            take_price=(float(r.get('take_price')) if r.get('take_price') is not None else None),
            status='OPEN',
        )
        positions[instrument] = p
        total_r += risk_r

    engine.state.positions = positions
    engine.state.open_exposure_r = float(total_r)
    return {'open_positions': len(positions), 'open_exposure_r': float(total_r)}
