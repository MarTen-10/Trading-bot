# Futures Brain v1

Futures-first trading brain scaffold (Bybit primary, OKX-ready).

## Scope (v1)
- Signal stub (replace with your strategy)
- Risk engine with hard caps
- Exchange adapters (Bybit wired, OKX stub)
- Dry-run executor + kill switch
- Journal logging for auditability

## Safety defaults
- `mode: paper`
- no order sent unless `mode: live` and `confirm_live` is true
- max daily loss lock
- per-trade risk cap
- max leverage cap

## Quick start
```bash
cd futures_brain
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python scripts/run_once.py
```

## Next
1. Wire Bybit auth keys in `.env`
2. Replace strategy logic in `brain/strategy.py`
3. Run paper soak (`mode: paper`) for at least several days
4. Enable live only with explicit approvals
