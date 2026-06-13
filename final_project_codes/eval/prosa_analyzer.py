"""
ProSA Persona Sensitivity Score (PSS) analyzer.

Implements the ProSA framework (Zhuo et al., 2024) adapted for multi-turn
customer service evaluation. For each case-architecture combination, computes
the instance-level sensitivity score Si as the mean pairwise absolute difference
in S_AnswerQuality across all C(3,2)=3 Persona pairs:
  Pairs: |Polite − Adversarial|, |Polite − VIP|, |Adversarial − VIP|

The overall PSS is the mean of Si across all cases. A lower PSS indicates
greater architectural stability across customer behavioral styles.

Usage:
  python -m eval.prosa_analyzer --logs-dir outputs/logs
  python -m eval.prosa_analyzer --logs-dir outputs/logs/outsample --oos
"""
