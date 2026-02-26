# Paper Runtime Ops

## Start
- `systemctl --user start horus-paper.service`

## Stop
- `systemctl --user stop horus-paper.service`

## Inspect
- `systemctl --user status horus-paper.service`
- `journalctl --user -u horus-paper.service -f`
- `python -m horus.runtime.status`

## Expected log events
- `SAFE_BLOCK_ENTRY`
- `RISK_EXPOSURE_CAP`
- `GATE_BLOCK`
- `ORDER_FILLED`
- `SAFE_TRIGGER`
- `RESOURCE_METRICS`
