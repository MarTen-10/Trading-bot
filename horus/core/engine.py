import hashlib
from dataclasses import dataclass, field

from horus.core.events import CandleEvent, OrderIntent, EngineDecision


@dataclass
class EngineState:
    safe_mode: bool = False
    open_exposure_r: float = 0.0
    max_open_exposure_r: float = 2.0


@dataclass
class Engine:
    strategy: any
    risk: any
    gate: any
    dbio: any
    logger: any
    state: EngineState = field(default_factory=EngineState)

    def process_event(self, event: CandleEvent) -> EngineDecision:
        signal = self.strategy.generate(event)
        if not signal:
            return EngineDecision(signal=None, intents=[])

        # SAFE hard gate before any entry intent
        if self.state.safe_mode:
            self.dbio.insert_governance('SAFE_BLOCK_ENTRY', signal['instrument'], 'breakout_v2', 'BLOCK', 'SAFE_MODE_ACTIVE', {'signal_id': signal['signal_id']})
            self.logger('WARNING', 'SAFE_BLOCK_ENTRY', signal=signal['signal_id'], reason='SAFE_MODE_ACTIVE')
            return EngineDecision(signal=signal, intents=[], veto_reason='SAFE_MODE_ACTIVE')

        allowed, reason, gate_meta = self.gate.allow(signal)
        if not allowed:
            self.dbio.insert_governance('GATE_VETO', signal['instrument'], 'breakout_v2', 'BLOCK', reason, gate_meta)
            self.logger('WARNING', 'GATE_BLOCK', signal=signal['signal_id'], reason=reason, meta=gate_meta)
            return EngineDecision(signal=signal, intents=[], veto_reason=reason)

        ok, r_reason = self.risk.allow(signal)
        if not ok:
            self.dbio.insert_governance('RISK_BLOCK', signal['instrument'], 'breakout_v2', 'BLOCK', r_reason, gate_meta)
            self.logger('WARNING', 'RISK_BLOCK', signal=signal['signal_id'], reason=r_reason, meta=gate_meta)
            return EngineDecision(signal=signal, intents=[], veto_reason=r_reason)

        qty, risk_d = self.risk.size(signal, equity=1000.0)
        # 1R = risk_dollars for each entry in this simplified model
        projected_r = self.state.open_exposure_r + 1.0
        if projected_r > self.state.max_open_exposure_r:
            self.dbio.insert_governance('RISK_EXPOSURE_CAP', signal['instrument'], 'breakout_v2', 'BLOCK', 'RISK_EXPOSURE_CAP', {
                'open_exposure_r': self.state.open_exposure_r,
                'attempt_r': 1.0,
                'max_open_exposure_r': self.state.max_open_exposure_r,
            })
            self.logger('WARNING', 'RISK_EXPOSURE_CAP', signal=signal['signal_id'], open_exposure_r=self.state.open_exposure_r, max_open_exposure_r=self.state.max_open_exposure_r)
            return EngineDecision(signal=signal, intents=[], veto_reason='RISK_EXPOSURE_CAP')

        intent_payload = f"{signal['signal_id']}|{event.instrument}|{event.timestamp.isoformat()}|{event.sequence_id}|intent"
        intent_id = hashlib.sha256(intent_payload.encode()).hexdigest()[:32]
        intent = OrderIntent(
            intent_id=intent_id,
            signal_id=signal['signal_id'],
            instrument=event.instrument,
            side=signal['side'],
            entry_px=float(signal['entry_px']),
            stop_px=float(signal['stop_px']),
            qty=float(qty),
            risk_dollars=float(risk_d),
            event_ts=signal['ts'],
        )
        self.state.open_exposure_r = projected_r
        return EngineDecision(signal=signal, intents=[intent])
