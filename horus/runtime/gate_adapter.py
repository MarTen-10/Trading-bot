#!/usr/bin/env python3
import json, os
from pathlib import Path

GATE = Path('/home/marten/.openclaw/workspace/horus/data/reports/runtime_gate_latest.json')
REGIME = Path('/home/marten/.openclaw/workspace/horus/data/reports/regime_labels_btc_latest.json')


def current_regime(instrument='BTCUSD'):
    if not REGIME.exists():
        return 'UNKNOWN'
    j = json.loads(REGIME.read_text())
    labels = j.get('labels', [])
    if not labels:
        return 'UNKNOWN'
    return labels[-1].get('regime', 'UNKNOWN')


def allow(signal: dict):
    regime = current_regime(signal['instrument'])
    required_regime = os.getenv('HORUS_REQUIRED_REGIME', 'TREND_NORMAL')
    if regime != required_regime:
        return False, 'regime_block', {'regime': regime, 'required_regime': required_regime}

    if GATE.exists():
        g = json.loads(GATE.read_text())
        if g.get('promotion_status') != 'PROMOTE':
            return False, 'promotion_reject', {
                'promotion_status': g.get('promotion_status'),
                'disable_status': g.get('disable_status'),
                'rolling_expectancy': g.get('rolling_expectancy', {}).get('latest')
            }
        return True, None, {
            'promotion_status': g.get('promotion_status'),
            'disable_status': g.get('disable_status'),
            'rolling_expectancy': g.get('rolling_expectancy', {}).get('latest'),
            'regime': regime
        }

    return False, 'gate_missing', {'regime': regime}
