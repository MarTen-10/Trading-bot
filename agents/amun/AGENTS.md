# Amun Agent Contract

Produces:
- Backtest and walk-forward reports
- Promotion recommendation packets

Output packet:
{
  "type": "research_report",
  "run_id": "uuid",
  "strategy_id": "string",
  "window": {"start":"ISO8601","end":"ISO8601"},
  "metrics": {
    "expectancy": 0.0,
    "max_drawdown": 0.0,
    "win_rate": 0.0,
    "profit_factor": 0.0,
    "sharpe": 0.0
  },
  "after_cost_positive": true,
  "recommendation": "PROMOTE|ITERATE|REJECT"
}
