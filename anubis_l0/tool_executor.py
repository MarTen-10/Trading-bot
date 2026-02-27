import os
import time
from typing import Callable, Any

from anubis_l0.budget import BudgetExceeded
from anubis_l0.retry import bounded_retry
from anubis_l0.router import gate_step


class ToolExecutor:
    def __init__(self, *, budget, logger, cache, model: str, limits):
        self.budget = budget
        self.logger = logger
        self.cache = cache
        self.model = model
        self.limits = limits

    def execute(self, *, step_id: str, tool_name: str, fn: Callable[[], Any], necessary: bool = True, cheapest_route: str = "tool:fast", cap: str = "default"):
        if os.getenv("ANUBIS_DISABLE_TOOLS") == "1" or os.getenv("ANUBIS_READONLY") == "1":
            self.logger.event("gate_block", step_id=step_id, reason="kill_switch_enabled", tool=tool_name)
            raise RuntimeError("blocked_by_kill_switch")

        gate = gate_step(necessary=necessary, cheapest_route=cheapest_route, cap=cap)
        if not gate["allowed"]:
            self.logger.event("gate_block", step_id=step_id, reason=gate["reason"], tool=tool_name)
            raise RuntimeError(gate["reason"])

        # pre-execution budget check
        self.budget.check_or_raise(step_id)

        cached = self.cache.get(tool_name, ttl_seconds=self.limits.cache_ttl_seconds)
        if cached is not None:
            self.logger.event(
                "action_end",
                step_id=step_id,
                action_type="tool",
                model=self.model,
                tool=tool_name,
                cache_hit=True,
                input_bytes=len(tool_name),
                output_bytes=len(str(cached)),
                tokens_in=0,
                tokens_out=0,
                cost_estimate=0.0,
                latency_ms=0,
            )
            # still enforce pre/post budget around cache return path
            self.budget.check_or_raise(step_id)
            return cached

        started = time.time()
        self.logger.event("action_start", step_id=step_id, action_type="tool", model=self.model, tool=tool_name)

        out, retries = bounded_retry(fn, attempts=self.limits.max_retries_per_action)
        latency = int((time.time() - started) * 1000)

        usage_in = 120
        usage_out = 40
        usd = 0.0003

        self.cache.set(tool_name, out)
        self.budget.record_usage(tool_calls=1, tokens_in=usage_in, tokens_out=usage_out, usd=usd)

        # post-execution budget check (overshoot guard)
        self.budget.check_or_raise(step_id)

        self.logger.event(
            "action_end",
            step_id=step_id,
            action_type="tool",
            model=self.model,
            tool=tool_name,
            input_bytes=len(tool_name),
            output_bytes=len(str(out)),
            tokens_in=usage_in,
            tokens_out=usage_out,
            cost_estimate=usd,
            latency_ms=latency,
            cache_hit=False,
            retries=retries,
            budget_remaining={
                "tool_calls": self.limits.max_tool_calls_per_run - self.budget.usage.tool_calls,
                "tokens": self.limits.max_tokens_per_run - (self.budget.usage.tokens_in + self.budget.usage.tokens_out),
                "usd_run": round(self.limits.max_usd_per_run - self.budget.usage.usd, 6),
            },
        )
        return out
