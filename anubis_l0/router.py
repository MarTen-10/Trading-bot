def gate_step(*, necessary: bool, cheapest_route: str, cap: str):
    if not necessary:
        return {"allowed": False, "reason": "blocked by L0 gate: not necessary"}
    return {"allowed": True, "route": cheapest_route, "cap": cap}


class ModelRouter:
    def __init__(self):
        self.default_model = "fast"

    def choose(self, *, high_stakes=False, low_confidence=False, user_requested_deep=False):
        if user_requested_deep or (high_stakes and low_confidence):
            return "strong", "escalation:high_stakes_or_user_request"
        return self.default_model, "cheap-first"
