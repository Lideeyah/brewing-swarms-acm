"""
Brewing SLA Orchestrator — Demo Runner
─────────────────────────────────────────────────────────────────────────────
Runs the complete governed execution lifecycle end-to-end.

No live Solana RPC required — escrow is simulated deterministically.
Real Claude API calls are made for all agents (ANTHROPIC_API_KEY required).

Usage
─────
  python3 demo.py
  python3 demo.py "Your custom goal here"
  python3 demo_script.py    ← presenter script with narration cues
"""
from __future__ import annotations

import os
import sys
import time

from brewing_sla_orchestrator import BrewingOrchestrator, _W
from escrow import JobStatus
from governance import GovernanceConfig

# ── Pre-canned demo goals ─────────────────────────────────────────────────────

_DEMO_GOALS = [
    # Goal 0 — default: competitive positioning
    (
        "Research what makes a strong autonomous AI agent marketplace submission, "
        "then write a 200-word positioning brief for the Brewing SLA Orchestrator "
        "that highlights governed execution, escrow-backed coordination, "
        "and SLA enforcement as its core differentiators"
    ),
    # Goal 1 — risk analysis
    (
        "Analyse the top 3 risks of deploying autonomous AI agents without "
        "SLA enforcement or escrow-backed payment settlement, "
        "then write a 200-word argument for why Brewing's governed model solves them"
    ),
    # Goal 2 — developer onboarding
    (
        "Research the Swarms multi-agent framework and write a concise developer "
        "guide for integrating the Brewing SLA Orchestrator as a callable Swarms agent"
    ),
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _check_env() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print()
        print("  ❌  ANTHROPIC_API_KEY is not set.")
        print("      Add it to your .env or export it:")
        print("      export ANTHROPIC_API_KEY=sk-ant-...")
        print()
        sys.exit(1)


def _print_header() -> None:
    W = _W
    print()
    print("╔" + "═" * (W - 2) + "╗")
    print("║" + "  BREWING SLA ORCHESTRATOR  ·  Swarms ACM Demo".ljust(W - 2) + "║")
    print("║" + "  Governed Autonomous Clearinghouse for AI Systems".ljust(W - 2) + "║")
    print("╠" + "═" * (W - 2) + "╣")
    print("║" + "  Framework  : Swarms multi-agent (claude-opus-4-6)".ljust(W - 2) + "║")
    print("║" + "  Escrow     : Simulated  (SOLANA_MODE=1 for live on-chain)".ljust(W - 2) + "║")
    print("║" + "  Mode       : Frenzy — deterministic, reproducible".ljust(W - 2) + "║")
    print("╚" + "═" * (W - 2) + "╝")
    print()


def _print_goal(goal: str) -> None:
    W = _W
    print("  GOAL")
    print("  " + "─" * (W - 4))
    import textwrap
    for line in textwrap.wrap(goal, W - 4):
        print(f"  {line}")
    print("  " + "─" * (W - 4))
    print()


def _print_escrow_audit(orchestrator: BrewingOrchestrator, elapsed: float) -> None:
    W   = _W
    jobs = orchestrator.escrow.all_jobs()

    print()
    print("─" * W)
    print("  ON-CHAIN ESCROW AUDIT")
    print("─" * W)
    print()

    if not jobs:
        print("  No jobs in ledger.")
        print()
        return

    for job in jobs:
        sla_ok = (
            not job.sla_breached
            or job.status in (JobStatus.COMPLETED, JobStatus.DISPUTED)
        )
        icon = (
            "✅" if job.status == JobStatus.COMPLETED else
            "⚠️ " if job.status == JobStatus.DISPUTED else
            "🕐"
        )
        status_label = job.status.value
        sla_label    = "SLA met" if sla_ok else "SLA BREACHED"

        print(f"  {icon}  #{job.job_id}  ·  {job.capability.upper()}  ·  {status_label}  ·  {sla_label}")
        print(f"       Score    : {job.verification_score}/10")
        print(f"       Payment  : {job.payment_usdc} USDC")
        tx_post = job.tx_signatures.get("post", "—")
        print(f"       tx_post  : {tx_post}")
        if "release" in job.tx_signatures:
            print(f"       tx_settle: {job.tx_signatures['release']}")
        if "dispute" in job.tx_signatures:
            print(f"       tx_dispute: {job.tx_signatures['dispute']}")
        print()

    total_settled  = sum(j.payment_usdc for j in jobs if j.status == JobStatus.COMPLETED)
    total_disputed = sum(j.payment_usdc for j in jobs if j.status == JobStatus.DISPUTED)
    fees           = orchestrator.escrow.collected_fees()

    print("  " + "─" * (W - 4))
    print(f"  Settled   {total_settled:.4f} USDC"
          f"   ·   Treasury  {fees:.4f} USDC"
          f"   ·   Disputed  {total_disputed:.4f} USDC")
    print("  " + "─" * (W - 4))
    print()
    print(f"  Completed in {elapsed:.1f}s")
    print()
    print("─" * W)
    print()


# ── Entry point ───────────────────────────────────────────────────────────────

def run_demo(goal: str | None = None) -> None:
    _check_env()
    _print_header()

    effective_goal = goal or _DEMO_GOALS[0]
    _print_goal(effective_goal)

    config = GovernanceConfig(
        verification_threshold=6,
        sla_seconds=120,
        max_subtasks=3,
        max_payment_usdc=1.0,
    )

    start   = time.time()
    agent   = BrewingOrchestrator(governance_config=config, verbose=True)
    agent.run(effective_goal)
    elapsed = time.time() - start

    _print_escrow_audit(agent, elapsed)


if __name__ == "__main__":
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    goal_arg = sys.argv[1] if len(sys.argv) > 1 else None
    run_demo(goal_arg)
