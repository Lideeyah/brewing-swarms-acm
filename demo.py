"""
Brewing SLA Orchestrator — Deterministic Demo
─────────────────────────────────────────────────────────────────────────────
Runs the complete governed execution lifecycle end-to-end.

No live Solana RPC required — escrow is simulated deterministically.
Real Claude API calls are made via Swarms agents (ANTHROPIC_API_KEY required).

Demo flow
─────────
  1.  Orchestrator receives a natural-language goal
  2.  Decomposer (Swarms Agent) breaks it into 2-3 governed sub-tasks
  3.  GovernanceEngine validates each: capability approved? payment within cap?
  4.  EscrowEngine posts each job — USDC locked with SLA timer
  5.  Worker agent (Swarms Agent, capability-specialised) executes the task
  6.  VerifierAgent (Swarms Agent) scores output 1-10
  7.  GovernanceEngine gate: score ≥ threshold → release; below → Disputed
  8.  EscrowEngine settles: payment released or escrowed in Disputed state
  9.  SynthesizerAgent assembles final executive deliverable
  10. Full SLA ledger printed with job IDs, scores, statuses, sim tx hashes

Usage
─────
  python demo.py
  python demo.py "Your custom goal here"

Environment
───────────
  ANTHROPIC_API_KEY  — required (real Claude API calls via Swarms)
  SOLANA_MODE=1      — optional (route escrow through live Solana program)
"""
from __future__ import annotations

import os
import sys
import time

from brewing_sla_orchestrator import BrewingOrchestrator
from escrow import JobStatus
from governance import GovernanceConfig

# ── Pre-canned demo goals ─────────────────────────────────────────────────────
_DEMO_GOALS = [
    # Goal 0 — default: positions Brewing in the agent-framework landscape
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


def _check_env() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print()
        print("  ❌  ANTHROPIC_API_KEY is not set.")
        print("      Add it to your .env or export it:")
        print("      export ANTHROPIC_API_KEY=sk-ant-...")
        print()
        sys.exit(1)


def _print_header() -> None:
    print()
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║    BREWING SLA ORCHESTRATOR  ·  Swarms ACM Demo                 ║")
    print("║    Governed Autonomous Clearinghouse for AI Systems              ║")
    print("╠══════════════════════════════════════════════════════════════════╣")
    print("║  Framework  : Swarms multi-agent (claude-opus-4-7)              ║")
    print("║  Escrow     : Simulated (SOLANA_MODE=1 for live Solana)         ║")
    print("║  Mode       : Frenzy — deterministic, reproducible              ║")
    print("╚══════════════════════════════════════════════════════════════════╝")
    print()


def _print_escrow_audit(orchestrator: BrewingOrchestrator) -> None:
    print()
    print("── On-Chain Escrow State Audit ─────────────────────────────────────")
    print()
    jobs = orchestrator.escrow.all_jobs()
    if not jobs:
        print("  (no jobs in ledger)")
        return

    for job in jobs:
        sla_ok = (
            not job.sla_breached
            or job.status in (JobStatus.COMPLETED, JobStatus.DISPUTED)
        )
        icon = "✅" if job.status == JobStatus.COMPLETED else (
               "⚠️ " if job.status == JobStatus.DISPUTED else "🕐")

        print(f"  {icon} #{job.job_id}  [{job.capability:<10}]  {job.status.value}")
        print(
            f"     payment = {job.payment_usdc} USDC  "
            f"|  score = {job.verification_score}/10  "
            f"|  SLA {'✅ met' if sla_ok else '⚠️  BREACHED'}"
        )
        print(f"     sim_tx_post    = {job.tx_signatures.get('post', '—')}")
        if "release" in job.tx_signatures:
            print(f"     sim_tx_release = {job.tx_signatures['release']}")
        if "dispute" in job.tx_signatures:
            print(f"     sim_tx_dispute = {job.tx_signatures['dispute']}")
        print()

    total_settled  = sum(
        j.payment_usdc for j in jobs if j.status == JobStatus.COMPLETED
    )
    total_disputed = sum(
        j.payment_usdc for j in jobs if j.status == JobStatus.DISPUTED
    )
    fees = orchestrator.escrow.collected_fees()

    print(f"  Protocol fees collected : {fees:.4f} USDC  (2.5% treasury)")
    print(f"  Total settled           : {total_settled:.2f} USDC")
    print(f"  Total in dispute        : {total_disputed:.2f} USDC  (escrowed)")
    print()
    print("─────────────────────────────────────────────────────────────────────")
    print()
    print("  ✅  Demo complete.")
    print()
    print("  Next steps:")
    print("    • Set SOLANA_MODE=1 and fund a Solana devnet wallet to run")
    print("      the same flow with real USDC escrow on-chain.")
    print("    • Swap the goal for any natural-language instruction and the")
    print("      orchestrator will decompose, delegate, verify, and settle it.")
    print()


def run_demo(goal: str | None = None) -> None:
    _check_env()
    _print_header()

    effective_goal = goal or _DEMO_GOALS[0]
    print(f"  Goal: {effective_goal}")
    print()

    # Demo uses slightly tighter config for speed (6/10 threshold, 120s SLA)
    config = GovernanceConfig(
        verification_threshold=6,
        sla_seconds=120,
        max_subtasks=3,
        max_payment_usdc=1.0,
    )

    start   = time.time()
    agent   = BrewingOrchestrator(governance_config=config, verbose=True)
    _result = agent.run(effective_goal)
    elapsed = time.time() - start

    print(f"  ⏱️   Orchestration completed in {elapsed:.1f}s")
    _print_escrow_audit(agent)


if __name__ == "__main__":
    # Load .env if present
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    goal_arg = sys.argv[1] if len(sys.argv) > 1 else None
    run_demo(goal_arg)
