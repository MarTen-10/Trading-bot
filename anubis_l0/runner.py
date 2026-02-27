import os
import time
import uuid
import fcntl

from anubis_l0.config import L0Limits
from anubis_l0.budget import BudgetController, BudgetExceeded
from anubis_l0.logger import JsonlLogger
from anubis_l0.router import ModelRouter, gate_step
from anubis_l0.retry import bounded_retry
from anubis_l0.cache import SimpleCache


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

        gate = gate_step(necessary=True, cheapest_route="tool:fast", cap="20 calls")
        if not gate["allowed"]:
            log.event("gate_block", reason=gate["reason"])
            log.event("run_end", summary=budget.summarize())
            return run_id, "blocked"

        steps = ["fetch_prices", "fail_once", "compute_signal", "persist"]
        if simulate_overrun:
            steps = [f"tool_{run_id}_{i}" for i in range(25)]

        for idx, step in enumerate(steps, start=1):
            step_id = f"s{idx}"
            budget.check_or_raise(step_id)

            cached = cache.get(step, ttl_seconds=limits.cache_ttl_seconds)
            if cached is not None:
                log.event(
                    "action_end",
                    step_id=step_id,
                    action_type="tool",
                    model=model,
                    tool=step,
                    cache_hit=True,
                    input_bytes=len(step),
                    output_bytes=len(str(cached)),
                    tokens_in=0,
                    tokens_out=0,
                    cost_estimate=0.0,
                    latency_ms=0,
                )
                continue

            started = time.time()
            log.event("action_start", step_id=step_id, action_type="tool", model=model, tool=step)
            try:
                out, retries = bounded_retry(lambda: _fake_tool_call(step), attempts=limits.max_retries_per_action)
                latency = int((time.time() - started) * 1000)
                cache.set(step, out)
                usage_in = 120
                usage_out = 40
                usd = 0.0003
                budget.record_usage(tool_calls=1, tokens_in=usage_in, tokens_out=usage_out, usd=usd)
                budget.check_or_raise(step_id)
                log.event(
                    "action_end",
                    step_id=step_id,
                    action_type="tool",
                    model=model,
                    tool=step,
                    input_bytes=len(step),
                    output_bytes=len(str(out)),
                    tokens_in=usage_in,
                    tokens_out=usage_out,
                    cost_estimate=usd,
                    latency_ms=latency,
                    cache_hit=False,
                    retries=retries,
                    budget_remaining={
                        "tool_calls": limits.max_tool_calls_per_run - budget.usage.tool_calls,
                        "tokens": limits.max_tokens_per_run - (budget.usage.tokens_in + budget.usage.tokens_out),
                        "usd_run": round(limits.max_usd_per_run - budget.usage.usd, 6),
                    },
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
