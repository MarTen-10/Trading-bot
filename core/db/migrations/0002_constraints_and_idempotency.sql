-- Migration v2: tighten constraints and idempotency support

ALTER TABLE trades
    ADD COLUMN IF NOT EXISTS trade_id UUID;

UPDATE trades
SET trade_id = id
WHERE trade_id IS NULL;

ALTER TABLE trades
    ALTER COLUMN trade_id SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'uq_trades_trade_id'
    ) THEN
        ALTER TABLE trades ADD CONSTRAINT uq_trades_trade_id UNIQUE (trade_id);
    END IF;
END $$;

ALTER TABLE trades
    DROP CONSTRAINT IF EXISTS trades_risk_ticket_hash_check;

ALTER TABLE trades
    ADD CONSTRAINT trades_risk_ticket_hash_check
    CHECK (risk_ticket_hash ~ '^[a-f0-9]{64}$');

ALTER TABLE trades
    DROP CONSTRAINT IF EXISTS trades_size_check;

ALTER TABLE trades
    ADD CONSTRAINT trades_size_check CHECK (size > 0);
