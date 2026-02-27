import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from anubis_l0.budget import BudgetController, BudgetExceeded
from anubis_l0.config import L0Limits
from anubis_l0.runner import run


class TestL0Adversarial(unittest.TestCase):
    def test_concurrency_collision(self):
        # simulate lock already held
        lock = '/tmp/anubis_l0_runner.lock'
        f = open(lock, 'w')
        import fcntl
        fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            _, status = run(simulate_overrun=False)
            self.assertEqual(status, 'blocked_concurrency')
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            f.close()

    def test_daily_rollover_resets(self):
        limits = L0Limits()
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, 'daily.json')
            yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime('%Y-%m-%d')
            with open(p, 'w', encoding='utf-8') as f:
                f.write('{"date":"%s","usd":999.0}' % yesterday)
            bc = BudgetController(limits, 'r1', state_path=p)
            self.assertEqual(bc._daily['date'], datetime.now(timezone.utc).strftime('%Y-%m-%d'))
            self.assertLessEqual(bc._daily.get('usd', 0.0), 0.0)

    def test_single_call_overshoot_halts(self):
        limits = L0Limits(max_tokens_per_run=100)
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, 'daily.json')
            bc = BudgetController(limits, 'r2', state_path=p)
            bc.record_usage(tool_calls=1, tokens_in=120, tokens_out=0, usd=0.0)
            with self.assertRaises(BudgetExceeded):
                bc.check_or_raise('overshoot')


if __name__ == '__main__':
    unittest.main()
