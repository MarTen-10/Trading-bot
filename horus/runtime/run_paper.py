#!/usr/bin/env python3
import json
import os
import resource
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
STATE = BASE / 'data/reports/runtime_state_latest.json'


def sh(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"cmd_failed {' '.join(cmd)} :: {p.stderr.strip()[:300]}")
    return p.stdout.strip()


def log(level: str, event: str, **fields):
    p = BASE / 'logs' / 'paper_runtime.log'
    p.parent.mkdir(parents=True, exist_ok=True)
    rec = {
        'level': level,
        'event': event,
        'ts': datetime.now(UTC).isoformat(),
        **fields,
    }
    line = json.dumps(rec, separators=(',', ':'))
    with p.open('a') as f:
        f.write(line + '\n')
    print(line, flush=True)


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
            'last_reconcile_ts': None,
        }
    return json.loads(STATE.read_text())


def load_runtime_config():
    cfg = {
        'risk_fraction': float(os.getenv('HORUS_RISK_FRACTION', '0.005')),
        'max_daily_loss_r': float(os.getenv('HORUS_MAX_DAILY_LOSS_R', '-3')),
        'data_stale_seconds': int(os.getenv('HORUS_DATA_STALE_SECONDS', '3')),
        'latency_threshold_ms': int(os.getenv('HORUS_LATENCY_THRESHOLD_MS', '1000')),
        'slippage_percentile': os.getenv('HORUS_SLIPPAGE_PERCENTILE', 'p75'),
        'breaker_daily_loss_r': float(os.getenv('HORUS_BREAKER_DAILY_LOSS_R', '-3')),
        'breaker_reject_count_10m': int(os.getenv('HORUS_BREAKER_REJECT_COUNT_10M', '5')),
        'breaker_fill_mismatch_polls': int(os.getenv('HORUS_BREAKER_FILL_MISMATCH_POLLS', '2')),
        'regime_required': os.getenv('HORUS_REQUIRED_REGIME', 'TREND_NORMAL'),
        'poll_seconds': int(os.getenv('HORUS_PAPER_LOOP_SECONDS', '300')),
        'resource_warn_rss_mb': int(os.getenv('HORUS_SOFT_RSS_WARN_MB', '500')),
        'cpu_log_seconds': int(os.getenv('HORUS_CPU_LOG_SECONDS', '60')),
    }
    log('INFO', 'STARTUP_CONFIG', config=cfg)
    return cfg


def main():
    cfg = load_runtime_config()
    universe = [x.strip().replace('USDT', 'USD') for x in os.getenv('HORUS_UNIVERSE', 'BTCUSDT,ETHUSDT,SOLUSDT').split(',') if x.strip()]
    stream = MarketStream(universe)
    strategy = StrategyEngine()
    risk = RiskEngine(risk_fraction=cfg['risk_fraction'], max_daily_loss_r=cfg['max_daily_loss_r'])
    metrics = load_metrics()
    state = load_state()

    poll_seconds = cfg['poll_seconds']
    last_reconcile = 0.0
    last_cpu_log = 0.0

    while True:
        t0 = time.time()
        try:
            sh(['python3', str(BASE / 'scripts/fetch_crypto_coinbase.py')])
            latest_btc = sorted((BASE / 'data/raw').glob('BTCUSD_15mo_1h_*.csv'))[-1]
            sh(['python3', str(BASE / 'backtester/regime_classifier.py'), '--csv', str(latest_btc), '--out', str(BASE / 'data/reports/regime_labels_btc_latest.json')])

            best_bt = sorted((BASE / 'data/backtests').glob('btc_autotune_bt_run3_sma_cross_fix_*.json'))
            if best_bt:
                best_bt = best_bt[-1]
                sh(['python3', str(BASE / 'backtester/monte_carlo_calibrated.py'), '--backtest-report', str(best_bt), '--out', str(BASE / 'data/reports/runtime_mc_latest.json'), '--equity', '1000', '--risk-pct', str(cfg['risk_fraction'])])
                sh(['python3', str(BASE / 'backtester/gate_engine.py'), '--backtest-report', str(best_bt), '--mc-report', str(BASE / 'data/reports/runtime_mc_latest.json'), '--out', str(BASE / 'data/reports/runtime_gate_latest.json')])

            produced = stream.poll()

            if produced == 0:
                snap0 = RuntimeSnapshot(
                    stale_seconds=cfg['data_stale_seconds'] + 2,
                    latency_p95_ms=stream.metrics.get('feed_latency_ms', 0),
                    spread_bps=8,
                    daily_median_spread_bps=7,
                    spread_shock_minutes=0,
                    reject_count_10m=0,
                    fill_mismatch_polls=0,
                    realized_r_day=state.get('realized_r_day', 0.0),
                )
                cb0 = evaluate(snap0)
                if cb0:
                    state['safe_mode'] = True
                    for e in cb0:
                        dbio.insert_cb(e['trigger'], e['threshold'], e['action'], json.dumps({'instrument': 'ALL'}))
                    log('ERROR', 'SAFE_MODE', triggers=cb0)

            while True:
                event = BUS.next()
                if event is None:
                    break

                log('INFO', 'CANDLE', instrument=event.instrument, tf=event.timeframe, event_timestamp=event.timestamp.isoformat(), seq_id=event.sequence_id)

                snap = RuntimeSnapshot(
                    stale_seconds=0 if produced > 0 else cfg['data_stale_seconds'] + 2,
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
                    log('ERROR', 'SAFE_TRIGGER', triggers=cb_events, instrument=event.instrument)
                    continue
                state['safe_mode'] = False

                signal = strategy.generate(event)
                if not signal:
                    continue

                metrics.signals_generated += 1
                dbio.insert_signal(signal['signal_id'], signal['ts'], signal['instrument'], 'breakout_v2', 'pending', '')

                allowed, reason, gate_meta = gate_adapter.allow(signal)
                if not allowed:
                    metrics.signals_vetoed += 1
                    dbio.insert_signal(signal['signal_id'], signal['ts'], signal['instrument'], 'breakout_v2', 'vetoed', reason)
                    dbio.insert_governance('GATE_VETO', signal['instrument'], 'breakout_v2', 'BLOCK', reason, json.dumps(gate_meta))
                    log('WARNING', 'GATE_BLOCK', signal=signal['signal_id'], reason=reason, meta=gate_meta)
                    continue

                ok, r_reason = risk.allow(signal)
                if not ok:
                    metrics.signals_vetoed += 1
                    dbio.insert_signal(signal['signal_id'], signal['ts'], signal['instrument'], 'breakout_v2', 'vetoed', r_reason)
                    dbio.insert_governance('RISK_BLOCK', signal['instrument'], 'breakout_v2', 'BLOCK', r_reason, json.dumps(gate_meta))
                    log('WARNING', 'RISK_BLOCK', signal=signal['signal_id'], reason=r_reason, meta=gate_meta)
                    continue

                qty, risk_d = risk.size(signal, equity=1000.0)
                signal['qty'] = qty
                signal['risk_dollars'] = risk_d

                dbio.insert_signal(signal['signal_id'], signal['ts'], signal['instrument'], 'breakout_v2', 'taken', '')
                log('INFO', 'GATE_ALLOW', signal=signal['signal_id'], meta=gate_meta)
                order, fill = place_order(signal)
                log('INFO', 'ORDER_FILLED', signal=signal['signal_id'], order=order['order_id'], fill_px=round(fill.fill_px, 8), qty=round(fill.fill_qty, 8))
                metrics.orders_sent += 1
                metrics.fills += 1
                metrics.current_regime = gate_meta.get('regime', 'UNKNOWN') if gate_meta else 'UNKNOWN'
                metrics.add_latency(stream.metrics.get('feed_latency_ms', 0.0))

                def _insert_trade(con):
                    with con.cursor() as cur:
                        cur.execute(
                            "INSERT INTO trades(trade_id, signal_id, entry_timestamp, exit_timestamp, realized_r, realized_pnl, mfe_r, mae_r, exit_reason) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(trade_id) DO UPDATE SET realized_r=EXCLUDED.realized_r,realized_pnl=EXCLUDED.realized_pnl",
                            (order['order_id'], signal['signal_id'], signal['ts'], signal['ts'], signal['target_r'], fill.fill_qty * (fill.fill_px - signal['entry_px']), signal['target_r'], -1.0, 'paper_instant')
                        )
                dbio.with_conn(_insert_trade)

            if time.time() - last_reconcile >= 30:
                rec = run_check()
                state['last_reconcile_ts'] = datetime.now(UTC).isoformat()
                if rec.get('mismatch'):
                    state['safe_mode'] = True
                    dbio.insert_cb('fill_mismatch', '>=2 polls', 'SAFE_RECONCILE_OPTIONAL_FLATTEN', json.dumps(rec))
                    log('ERROR', 'SAFE_RECONCILE', rec=rec)
                last_reconcile = time.time()

            if time.time() - last_cpu_log >= cfg['cpu_log_seconds']:
                rss_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
                cpu = float(sh(['bash', '-lc', f"ps -p {os.getpid()} -o %cpu= | xargs"]) or 0.0)
                level = 'WARNING' if rss_mb > cfg['resource_warn_rss_mb'] else 'INFO'
                log(level, 'RESOURCE_METRICS', rss_mb=round(rss_mb, 2), cpu_percent=cpu)
                last_cpu_log = time.time()

            metrics.save()
            save_state(state)

        except Exception as e:
            dbio.insert_cb('runtime_error', 'exception', 'SAFE_AND_ALERT', json.dumps({'error': str(e)}))
            state['safe_mode'] = True
            save_state(state)
            log('ERROR', 'SAFE_RUNTIME_EXCEPTION', error=str(e))

        dt = time.time() - t0
        time.sleep(max(1, poll_seconds - int(dt)))


if __name__ == '__main__':
    main()
