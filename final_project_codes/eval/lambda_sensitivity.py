"""
Lambda sensitivity analysis for NetValue / ΔMB.

Sweeps lambda across a range and checks whether architecture rankings
and ΔMB sign stability change — providing post-hoc justification for
the fixed lambda=0.01 used in the main evaluation.

Output:
  outputs/figures/fig_lambda_sensitivity_is.png
  outputs/figures/fig_lambda_sensitivity_oos.png
  outputs/reports/lambda_sensitivity_results.csv
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────────────
IS_CSV  = Path("outputs/reports/s_agent_results_full.csv")
OOS_CSV = Path("outputs/reports/oos_s_agent_results.csv")
OUT_DIR = Path("outputs/figures")
OUT_DIR.mkdir(parents=True, exist_ok=True)

LAMBDAS = np.unique(np.round(np.concatenate([
    np.arange(0.001, 0.010, 0.001),   # 0.001 – 0.009 (step 0.001)
    np.arange(0.010, 0.105, 0.010),   # 0.010 – 0.100 (step 0.010)
    np.arange(0.150, 0.550, 0.050),   # 0.150 – 0.500 (step 0.050)
]), 4))

ARCH_ORDER  = ["PlanExecute", "ReAct", "Single-slot", "Reflection"]
COLORS      = {"PlanExecute": "#2E86C1", "ReAct": "#E67E22",
               "Single-slot": "#27AE60", "Reflection": "#8E44AD"}
BASELINE    = "Single-slot"
LAMBDA_REF  = 0.01   # value used in the paper


# ── Core computation ─────────────────────────────────────────────────────────

def compute_delta_mb_sweep(df: pd.DataFrame) -> pd.DataFrame:
    """For every lambda, compute per-architecture mean NetValue and ΔMB."""
    rows = []
    for lam in LAMBDAS:
        df["nv"] = df["v_i"] * df["s_agent"] / 100.0 - lam * df["proxy_cost"]
        means = df.groupby("agent_type")["nv"].mean()
        baseline_nv = means.get(BASELINE, 0.0)
        for arch, nv in means.items():
            rows.append({
                "lambda": lam,
                "agent_type": arch,
                "net_value": round(nv, 4),
                "delta_mb": round(nv - baseline_nv, 4),
            })
    return pd.DataFrame(rows)


def rank_at_lambda(sweep: pd.DataFrame, lam: float) -> dict:
    """Return {arch: rank} at a specific lambda (rank 1 = best ΔMB)."""
    sub = sweep[np.isclose(sweep["lambda"], lam)].copy()
    sub = sub[sub["agent_type"] != BASELINE].sort_values("delta_mb", ascending=False)
    return {row.agent_type: i + 1 for i, row in enumerate(sub.itertuples())}


def find_crossovers(sweep: pd.DataFrame) -> list[dict]:
    """Detect lambda values where any two architectures swap ΔMB ranking."""
    archs = [a for a in ARCH_ORDER if a != BASELINE]
    pivot = sweep[sweep["agent_type"].isin(archs)].pivot(
        index="lambda", columns="agent_type", values="delta_mb"
    )
    events = []
    prev_order = None
    for lam, row in pivot.iterrows():
        curr_order = tuple(row.sort_values(ascending=False).index.tolist())
        if prev_order is not None and curr_order != prev_order:
            events.append({"lambda": lam, "new_order": list(curr_order)})
        prev_order = curr_order
    return events


def find_sign_flip(sweep: pd.DataFrame) -> dict:
    """Return the lowest lambda where each arch's ΔMB first turns negative."""
    flips = {}
    for arch in ARCH_ORDER:
        if arch == BASELINE:
            continue
        sub = sweep[sweep["agent_type"] == arch].sort_values("lambda")
        neg = sub[sub["delta_mb"] < 0]
        flips[arch] = round(float(neg["lambda"].iloc[0]), 4) if len(neg) else None
    return flips


# ── Plotting ─────────────────────────────────────────────────────────────────

def plot_sweep(sweep: pd.DataFrame, title: str, out_path: Path,
               crossovers: list, sign_flips: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    fig.suptitle(title, fontsize=13, fontweight="bold")

    for ax_idx, (metric, ylabel) in enumerate([
        ("net_value", "Mean NetValue"),
        ("delta_mb",  "ΔMB (vs Single-slot)"),
    ]):
        ax = axes[ax_idx]
        for arch in ARCH_ORDER:
            sub = sweep[sweep["agent_type"] == arch]
            ax.plot(sub["lambda"], sub[metric],
                    label=arch, color=COLORS[arch], linewidth=2)

        ax.axvline(LAMBDA_REF, color="red", linestyle="--",
                   linewidth=1.2, label=f"λ={LAMBDA_REF} (paper)")
        if metric == "delta_mb":
            ax.axhline(0, color="gray", linestyle=":", linewidth=1)

        ax.set_xlabel("λ (cost sensitivity)", fontsize=10)
        ax.set_ylabel(ylabel, fontsize=10)
        ax.xaxis.set_major_formatter(mticker.FormatStrFormatter("%.3f"))
        ax.legend(fontsize=9)
        ax.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved → {out_path}")


# ── Main ─────────────────────────────────────────────────────────────────────

def analyse(csv_path: Path, label: str, fig_name: str) -> pd.DataFrame:
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")

    df = pd.read_csv(csv_path)
    sweep = compute_delta_mb_sweep(df)

    crossovers = find_crossovers(sweep)
    sign_flips = find_sign_flip(sweep)

    # ── Print summary ────────────────────────────────────────────────────────
    ref_ranks = rank_at_lambda(sweep, LAMBDA_REF)
    print(f"\nRanking at λ={LAMBDA_REF}: {ref_ranks}")

    if crossovers:
        print(f"\nRanking crossovers detected ({len(crossovers)}):")
        for ev in crossovers:
            print(f"  λ={ev['lambda']:.4f}  →  new order: {ev['new_order']}")
    else:
        print("\nNo ranking crossovers across entire λ range — ranking is fully stable.")

    print("\nΔMB sign flip (turns negative) at λ =")
    for arch, lam in sign_flips.items():
        if lam:
            print(f"  {arch:14s}: λ={lam}")
        else:
            print(f"  {arch:14s}: stays positive across all tested λ")

    # ── Plot ─────────────────────────────────────────────────────────────────
    plot_sweep(
        sweep,
        title=f"Lambda Sensitivity — {label}",
        out_path=OUT_DIR / fig_name,
        crossovers=crossovers,
        sign_flips=sign_flips,
    )

    sweep["dataset"] = label
    return sweep


if __name__ == "__main__":
    is_sweep  = analyse(IS_CSV,  "In-Sample (IS)",       "fig_lambda_sensitivity_is.png")
    oos_sweep = analyse(OOS_CSV, "Out-of-Sample (OOS)",  "fig_lambda_sensitivity_oos.png")

    combined = pd.concat([is_sweep, oos_sweep], ignore_index=True)
    out_csv = Path("outputs/reports/lambda_sensitivity_results.csv")
    combined.to_csv(out_csv, index=False)
    print(f"\nFull sweep saved → {out_csv}")
