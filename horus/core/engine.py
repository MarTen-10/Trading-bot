import hashlib
from dataclasses import dataclass, field

from horus.core.events import CandleEvent, OrderIntent, EngineDecision


@dataclass
class Position:
    position_id: str
    signal_id: str
    instrument: str
    side: str
    entry_ts: str
    entry_sequence_id: int
    entry_price: float
    risk_r: float
    qty: float
    stop_price: float
    take_price: float | None
    status: str = 'OPEN'
    exit_ts: str | None = None
    exit_price: float | None = None
    exit_reason: str | None = None


@dataclass
class EngineState:
    safe_mode: bool = False
    open_exposure_r: float = 0.0
    max_open_exposure_r: float = 2.0
    exit_after_candles: int = 6
    positions: dict[str, Position] = field(default_factory=dict)


@dataclass
class Engine:
    strategy: any
    risk: any
    gate: any
    dbio: any
    logger: any
    state: EngineState = field(default_factory=EngineState)

    def _exit_intent_if_due(self, event: CandleEvent) -> list[OrderIntent]:
        pos = self.state.positions.get(event.instrument)
        if not pos or pos.status != 'OPEN':
            return []

        candles_since_entry = max(0, int(event.sequence_id - pos.entry_sequence_id))
        if candles_since_entry < int(self.state.exit_after_candles):
            return []

        side = 'sell' if pos.side == 'buy' else 'buy'
        payload = f"{pos.position_id}|{event.instrument}|{event.timestamp.isoformat()}|{event.sequence_id}|exit"
        intent_id = hashlib.sha256(payload.encode()).hexdigest()[:32]
        exit_intent = OrderIntent(
            intent_id=intent_id,
            signal_id=pos.signal_id,
            instrument=event.instrument,
            side=side,
            entry_px=float(event.close),
            stop_px=float(pos.stop_price),
            qty=float(pos.qty),
            risk_dollars=float(pos.risk_r),
            event_ts=event.timestamp.isoformat(),
            intent_type='EXIT',
            position_id=pos.position_id,
            exit_reason='time_exit',
        )

        # deterministic state transition on exit intent creation
        pos.status = 'CLOSED'
        pos.exit_ts = event.timestamp.isoformat()
        pos.exit_price = float(event.close)
        pos.exit_reason = 'time_exit'
        self.state.open_exposure_r = max(0.0, float(self.state.open_exposure_r) - float(pos.risk_r))
        self.state.positions.pop(event.instrument, None)

        return [exit_intent]

    def process_event(self, event: CandleEvent) -> EngineDecision:
        intents: list[OrderIntent] = []

        # exits are evaluated every candle, independent of new entry signals
        intents.extend(self._exit_intent_if_due(event))

        signal = self.strategy.generate(event)
        if not signal:
            return EngineDecision(signal=None, intents=intents)

        # SAFE hard gate before any entry intent
        if self.state.safe_mode:
            self.dbio.insert_governance('SAFE_BLOCK_ENTRY', signal['instrument'], 'breakout_v2', 'BLOCK', 'SAFE_MODE_ACTIVE', {'signal_id': signal['signal_id']})
            self.logger('WARNING', 'SAFE_BLOCK_ENTRY', signal=signal['signal_id'], reason='SAFE_MODE_ACTIVE')
            return EngineDecision(signal=signal, intents=intents, veto_reason='SAFE_MODE_ACTIVE')

        if signal['instrument'] in self.state.positions:
            self.dbio.insert_governance('POSITION_EXISTS', signal['instrument'], 'breakout_v2', 'BLOCK', 'POSITION_ALREADY_OPEN', {'signal_id': signal['signal_id']})
            self.logger('WARNING', 'POSITION_EXISTS', signal=signal['signal_id'], reason='POSITION_ALREADY_OPEN')
            return EngineDecision(signal=signal, intents=intents, veto_reason='POSITION_ALREADY_OPEN')

        allowed, reason, gate_meta = self.gate.allow(signal)
        if not allowed:
            self.dbio.insert_governance('GATE_VETO', signal['instrument'], 'breakout_v2', 'BLOCK', reason, gate_meta)
            self.logger('WARNING', 'GATE_BLOCK', signal=signal['signal_id'], reason=reason, meta=gate_meta)
            return EngineDecision(signal=signal, intents=intents, veto_reason=reason)

        ok, r_reason = self.risk.allow(signal)
        if not ok:
            self.dbio.insert_governance('RISK_BLOCK', signal['instrument'], 'breakout_v2', 'BLOCK', r_reason, gate_meta)
            self.logger('WARNING', 'RISK_BLOCK', signal=signal['signal_id'], reason=r_reason, meta=gate_meta)
            return EngineDecision(signal=signal, intents=intents, veto_reason=r_reason)

        qty, risk_d = self.risk.size(signal, equity=1000.0)
        projected_r = self.state.open_exposure_r + 1.0
        if projected_r > self.state.max_open_exposure_r:
            self.dbio.insert_governance('RISK_EXPOSURE_CAP', signal['instrument'], 'breakout_v2', 'BLOCK', 'RISK_EXPOSURE_CAP', {
                'open_exposure_r': self.state.open_exposure_r,
                'attempt_r': 1.0,
                'max_open_exposure_r': self.state.max_open_exposure_r,
            })
            self.logger('WARNING', 'RISK_EXPOSURE_CAP', signal=signal['signal_id'], open_exposure_r=self.state.open_exposure_r, max_open_exposure_r=self.state.max_open_exposure_r)
            return EngineDecision(signal=signal, intents=intents, veto_reason='RISK_EXPOSURE_CAP')

        intent_payload = f"{signal['signal_id']}|{event.instrument}|{event.timestamp.isoformat()}|{event.sequence_id}|intent"
        intent_id = hashlib.sha256(intent_payload.encode()).hexdigest()[:32]
        entry_intent = OrderIntent(
            intent_id=intent_id,
            signal_id=signal['signal_id'],
            instrument=event.instrument,
            side=signal['side'],
            entry_px=float(signal['entry_px']),
            stop_px=float(signal['stop_px']),
            qty=float(qty),
            risk_dollars=float(risk_d),
            event_ts=signal['ts'],
            intent_type='ENTRY',
            position_id=intent_id,
        )

        # deterministic position/open exposure state update on entry intent
        self.state.open_exposure_r = projected_r
        self.state.positions[event.instrument] = Position(
            position_id=intent_id,
            signal_id=signal['signal_id'],
            instrument=event.instrument,
            side=signal['side'],
            entry_ts=signal['ts'],
            entry_sequence_id=event.sequence_id,
            entry_price=float(signal['entry_px']),
            risk_r=1.0,
            qty=float(qty),
            stop_price=float(signal['stop_px']),
            take_price=None,
        )

        intents.append(entry_intent)
        return EngineDecision(signal=signal, intents=intents)
