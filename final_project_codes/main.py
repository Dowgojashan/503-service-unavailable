"""
main.py — Entry point for running in-sample (IS) evaluation experiments.

This script runs the full IS batch evaluation:
  - Loads all 150 IS cases from data/fact_sheets.json
  - Runs each case across 4 architectures (Single-slot, ReAct, Reflection, PlanExecute)
    and 3 Personas (Polite, Adversarial, VIP) via DialogueRunner
  - Saves conversation logs to outputs/logs/{Persona}/{Agent}/

For OOS evaluation, use run_oos_batch.py instead.
For metric computation, run: python -m eval.metrics --logs-dir outputs/logs
"""
