# Determinism Notes

- Decision IDs are hash-based from canonical event/signal payloads only.
- `ts_event` comes from market data and is used for decision objects.
- Wall clock (`datetime.now`, `time.time`) is used for ops scheduling and logging only.
- PostgreSQL `now()` defaults are audit metadata only.
- Engine decision flow does not query DB insert timestamps for entry/exit decisions.
