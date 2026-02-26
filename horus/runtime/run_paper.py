#!/usr/bin/env python3
import json
import os
import subprocess
import time
from datetime import datetime, UTC
from pathlib import Path

from horus.runtime.event_bus import BUS
from horus.runtime.market_stream import MarketStream
from horus.runtime.metrics import load as load_metrics
from horus.runtime.strategy import StrategyEngine
from horus.runtime.risk_engine import RiskEngine
from horus.runtime import gate_adapter
from horus.runtime.paper_execution import place_order
from horus.runtime.reconciliation import run_check
from horus.runtime.circuit_breakers import RuntimeSnapshot, evaluate
from horus.runtime import dbio

BASE = Path('/home/marten/.openclaw/workspace/horus')
STATE = BASE/'data/reports/runtime_state_latest.json'


def sh(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"cmd_failed {' '.join(cmd)} :: {p.stderr.strip()[:300]}")
    return p.stdout.strip()


def save_state(state):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2))


def load_state():
    if not STATE.exists():
        return {
            'safe_mode': False,
            'active_model_id': 'rule_based_v2',
            'disable_flags': {},
            'realized_r_day': 0.0,
            'positions': {'open_positions': 0},
            'last_reconcile_ts': None
        }
    return json.loads(STATE.read_text())


def main():
    universe = [x.strip().replace('USDT', 'USD') for x in os.getenv('HORUS_UNIVERSE', 'BTCUSDT,ETHUSDT,SOLUSDT').split(',') if x.strip()]
    stream = MarketStream(universe)
    strategy = StrategyEngine()
    risk = RiskEngine(risk_fraction=float(os.getenv('HORUS_RISK_FRACTION', '0.005')), max_daily_loss_r=float(os.getenv('HORUS_MAX_DAILY_LOSS_R', '-3')))
    metrics = load_metrics()
    state = load_state()

    poll_seconds = int(os.getenv('HORUS_PAPER_LOOP_SECONDS', '5'))
    last_reconcile = 0.0

    while True:
        t0 = time.time()
        try:
            # refresh feeds and gate artifacts
            sh(['python3', str(BASE/'scripts/fetch_crypto_coinbase.py')])
            latest_btc = sorted((BASE/'data/raw').glob('BTCUSD_15mo_1h_*.csv'))[-1]
            sh(['python3', str(BASE/'backtester/regime_classifier.py'), '--csv', str(latest_btc), '--out', str(BASE/'data/reports/regime_labels_btc_latest.json')])

            best_bt = sorted((BASE/'data/backtests').glob('btc_autotune_bt_run3_sma_cross_fix_*.json'))
            if best_bt:
                best_bt = best_bt[-1]
                sh(['python3', str(BASE/'backtester/monte_carlo_calibrated.py'), '--backtest-report', str(best_bt), '--out', str(BASE/'data/reports/runtime_mc_latest.json'), '--equity', '1000', '--risk-pct', os.getenv('HORUS_RISK_FRACTION', '0.005')])
                sh(['python3', str(BASE/'backtester/gate_engine.py'), '--backtest-report', str(best_bt), '--mc-report', str(BASE/'data/reports/runtime_mc_latest.json'), '--out', str(BASE/'data/reports/runtime_gate_latest.json')])

            # market adapter emits canonical events
            produced = stream.poll()

            # process queue
            while True:
                event = BUS.next()
                if event is None:
                    break

                # circuit breaker check uses runtime metrics
                snap = RuntimeSnapshot(
                    stale_seconds=0 if produced > 0 else 5,
                    latency_p95_ms=stream.metrics.get('feed_latency_ms', 0),
                    spread_bps=8,
                    daily_median_spread_bps=7,
                    spread_shock_minutes=0,
                    reject_count_10m=0,
                    fill_mismatch_polls=0,
                    realized_r_day=state.get('realized_r_day', 0.0),
                )
                cb_events = evaluate(snap)
                if cb_events:
                    state['safe_mode'] = True
                    for e in cb_events:
                        dbio.insert_cb(e['trigger'], e['threshold'], e['action'], json.dumps({'instrument': event.instrument}))
                    continue
                state['safe_mode'] = False

                signal = strategy.generate(event)
                if not signal:
                    continue

                metrics.signals_generated += 1

                allowed, reason, gate_meta = gate_adapter.allow(signal)
                if not allowed:
                    metrics.signals_vetoed += 1
                    dbio.insert_governance('GATE_VETO', signal['instrument'], 'breakout_v2', 'BLOCK', reason, json.dumps(gate_meta))
                    continue

                ok, r_reason = risk.allow(signal)
                if not ok:
                    metrics.signals_vetoed += 1
                    dbio.insert_governance('RISK_BLOCK', signal['instrument'], 'breakout_v2', 'BLOCK', r_reason, json.dumps(gate_meta))
                    continue

                qty, risk_d = risk.size(signal, equity=1000.0)
                signal['qty'] = qty
                signal['risk_dollars'] = risk_d

                order, fill = place_order(signal)
                metrics.orders_sent += 1
                metrics.fills += 1
                metrics.current_regime = gate_meta.get('regime', 'UNKNOWN') if gate_meta else 'UNKNOWN'
                metrics.add_latency(stream.metrics.get('feed_latency_ms', 0.0))

                # minimal trade row write (open+close in paper immediate model)
                dbio.with_sqlite(lambda con: con.execute(
                    "INSERT OR REPLACE INTO trades(trade_id, signal_id, entry_ts, exit_ts, realized_r, realized_pnl, mfe_r, mae_r, exit_reason) VALUES(?,?,?,?,?,?,?,?,?)",
                    (order['order_id'], signal['signal_id'], signal['ts'], signal['ts'], signal['target_r'], fill.fill_qty*(fill.fill_px-signal['entry_px']), signal['target_r'], -1.0, 'paper_instant')
                ))

            # reconciliation every 30s
            if time.time() - last_reconcile >= 30:
                rec = run_check()
                state['last_reconcile_ts'] = datetime.now(UTC).isoformat()
                if rec.get('mismatch'):
                    state['safe_mode'] = True
                    dbio.insert_cb('fill_mismatch', '>=2 polls', 'SAFE_RECONCILE_OPTIONAL_FLATTEN', json.dumps(rec))
                last_reconcile = time.time()

            metrics.save()
            save_state(state)

        except Exception as e:
            dbio.insert_cb('runtime_error', 'exception', 'SAFE_AND_ALERT', json.dumps({'error': str(e)}))
            state['safe_mode'] = True
            save_state(state)

        dt = time.time() - t0
        time.sleep(max(1, poll_seconds - int(dt)))


if __name__ == '__main__':
    main()
