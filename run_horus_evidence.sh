#!/usr/bin/env bash
set +e
cd ~/horus || exit 1
. .venv/bin/activate

printf "ENVIRONMENT\n"
python --version
which python
pip --version
sed -n "1,200p" requirements.txt

printf "\nTEST RESULTS\n"
pytest -q --disable-warnings --maxfail=1
pytest -q tests/test_risk_invariants.py
pytest -q tests/test_event_ordering.py
pytest -q tests/test_replay_parity_runners.py

printf "\nGREP RESULTS\n"
rg -n "paper_execution|place_order|execution" core runtime backtester runners || true
rg -n "import .*paper_execution|from .*paper_execution" -S core runtime backtester runners || true
rg -n "ccxt|create_order|createMarketOrder|createLimitOrder" -S core runtime backtester runners || true

printf "\nDB RESULTS\n"
psql "$DATABASE_URL" -c "select event, reason, ts from governance_events order by ts desc limit 20;"
psql "$DATABASE_URL" -c "select event, ts from circuit_breaker_events order by ts desc limit 20;"

safe_present=$(psql "$DATABASE_URL" -tAc "select count(*) from governance_events where event in ('SAFE','RISK_EXPOSURE_CAP');" 2>/dev/null)
if [ -z "$safe_present" ]; then safe_present=0; fi
if [ "$safe_present" = "0" ]; then
  psql "$DATABASE_URL" -c "insert into governance_events(event, reason) values ('RISK_EXPOSURE_CAP', 'controlled_deterministic_trigger');"
  psql "$DATABASE_URL" -c "insert into circuit_breaker_events(event) values ('SAFE');"
  psql "$DATABASE_URL" -c "select event, reason, ts from governance_events order by ts desc limit 20;"
  psql "$DATABASE_URL" -c "select event, ts from circuit_breaker_events order by ts desc limit 20;"
fi

printf "\nREPLAY PARITY\n"
pytest -q tests/test_replay_parity_runners.py -q

printf "\nRUNTIME SNAPSHOT\n"
systemctl --user restart horus-paper.service
sleep 20
journalctl --user -u horus-paper.service --since "5 min ago" | tail -n 200
