import os
import uuid
import fcntl

from anubis_l0.config import L0Limits
from anubis_l0.budget import BudgetController, BudgetExceeded
from anubis_l0.logger import JsonlLogger
from anubis_l0.router import ModelRouter
from anubis_l0.cache import SimpleCache
from anubis_l0.tool_executor import ToolExecutor


def _fake_tool_call(name: str):
    if name == "fail_once":
        if not hasattr(_fake_tool_call, "_failed"):
            _fake_tool_call._failed = True
            raise RuntimeError("transient_error")
    return {"ok": True, "tool": name, "output": "done"}


def run(simulate_overrun: bool = False):
    run_id = f"l0-{uuid.uuid4().hex[:10]}"
    limits = L0Limits()

    lock_file = "/tmp/anubis_l0_runner.lock"
    lk = open(lock_file, "w")
    try:
        fcntl.flock(lk.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lk.close()
        return run_id, "blocked_concurrency"

    budget = BudgetController(limits, run_id)
    log = JsonlLogger(run_id)
    router = ModelRouter()
    cache = SimpleCache()

    try:
        log.event("run_start", limits=budget.summarize()["limits"])

        if os.getenv("ANUBIS_DISABLE_TOOLS") == "1" or os.getenv("ANUBIS_READONLY") == "1":
            log.event("gate_block", reason="kill_switch_enabled")
            log.event("run_end", summary=budget.summarize())
            return run_id, "blocked"

        model, reason = router.choose(high_stakes=False, low_confidence=False, user_requested_deep=False)
        log.event("model_selected", model=model, reason=reason, temperature=limits.default_temperature)

        executor = ToolExecutor(budget=budget, logger=log, cache=cache, model=model, limits=limits)

        steps = ["fetch_prices", "fail_once", "compute_signal", "persist"]
        if simulate_overrun:
            steps = [f"tool_{run_id}_{i}" for i in range(25)]

        for idx, step in enumerate(steps, start=1):
            step_id = f"s{idx}"
            try:
                executor.execute(
                    step_id=step_id,
                    tool_name=step,
                    fn=lambda s=step: _fake_tool_call(s),
                    necessary=True,
                    cheapest_route="tool:fast",
                    cap="20 calls",
                )
            except BudgetExceeded as e:
                log.event("error", step_id=step_id, error=str(e))
                log.event("run_end", summary=budget.summarize())
                return run_id, "halted_budget"
            except Exception as e:
                log.event("error", step_id=step_id, error=str(e))
                log.event("run_end", summary=budget.summarize())
                return run_id, "halted_error"

        log.event("run_end", summary=budget.summarize())
        return run_id, "ok"
    finally:
        try:
            fcntl.flock(lk.fileno(), fcntl.LOCK_UN)
        except Exception:
            pass
        lk.close()


if __name__ == "__main__":
    run_id, status = run(simulate_overrun=bool(os.getenv("L0_SIM_OVER", "0") == "1"))
    print(run_id, status)
