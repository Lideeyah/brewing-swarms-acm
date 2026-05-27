"""
Brewing Governance Layer
─────────────────────────────────────────────────────────────────────────────
Deterministic access-control and verification rules governing how the
orchestrator may post jobs, delegate to workers, and release payments.

Mirrors the Anchor program's owner-gate and SLA enforcement constraints.
All rules are evaluated synchronously — no probabilistic logic, no LLM-in-the-loop.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class GovernanceConfig:
    """
    Immutable governance parameters.  Change these to tune the orchestrator's
    risk tolerance, payout caps, and quality thresholds without touching logic.
    """
    owner:                  str        = "brewing-orchestrator"
    verification_threshold: int        = 7     # /10 — minimum to auto-release escrow
    max_payment_usdc:       float      = 1.0   # per-subtask payment cap
    max_subtasks:           int        = 4     # decomposition ceiling
    sla_seconds:            int        = 300   # 5-minute SLA per subtask
    auto_release:           bool       = True  # release payment without human gate
    require_verification:   bool       = True  # block release if score below threshold
    slash_on_sla_breach:    bool       = True  # auto-slash workers who miss deadline
    approved_capabilities:  list[str]  = field(
        default_factory=lambda: ["research", "coding", "trading", "writing"]
    )


class GovernanceViolation(Exception):
    """Raised when a governance rule is violated."""
    pass


class GovernanceEngine:
    """
    Stateless rule evaluator.  All methods raise GovernanceViolation on breach.

    Usage
    -----
    gov = GovernanceEngine()
    gov.validate_post("research", 0.10, caller="orchestrator")   # OK
    gov.validate_post("hacking", 0.10, caller="orchestrator")    # raises
    gov.validate_release(score=8, caller="orchestrator")          # OK
    gov.validate_release(score=5, caller="orchestrator")          # raises
    """

    def __init__(self, config: Optional[GovernanceConfig] = None) -> None:
        self.config = config or GovernanceConfig()

    # ── Post-job validation ───────────────────────────────────────────────────

    def validate_post(
        self,
        capability: str,
        payment_usdc: float,
        caller: str,
    ) -> None:
        """
        Ensure a job-post request satisfies governance rules.
        Raises GovernanceViolation if any rule is breached.
        """
        if capability not in self.config.approved_capabilities:
            raise GovernanceViolation(
                f"Capability '{capability}' is not on the approved list: "
                f"{self.config.approved_capabilities}. "
                "Add it to GovernanceConfig.approved_capabilities to enable."
            )
        if payment_usdc > self.config.max_payment_usdc:
            raise GovernanceViolation(
                f"Proposed payment {payment_usdc} USDC exceeds governance cap "
                f"{self.config.max_payment_usdc} USDC. Lower the payment or raise the cap."
            )
        if payment_usdc <= 0:
            raise GovernanceViolation(
                "Payment must be > 0 USDC."
            )

    # ── Release validation ────────────────────────────────────────────────────

    def validate_release(self, score: int, caller: str) -> None:
        """
        Block payment release if quality score fails governance threshold.
        On failure the escrow state transitions to Disputed — funds are held.
        """
        if not self.config.require_verification:
            return
        if score < self.config.verification_threshold:
            raise GovernanceViolation(
                f"Quality score {score}/10 is below the governance threshold "
                f"{self.config.verification_threshold}/10. "
                "Payment release blocked — job status set to Disputed."
            )

    # ── Orchestration validation ──────────────────────────────────────────────

    def validate_orchestration(self, num_subtasks: int, caller: str) -> None:
        """Ensure decomposition doesn't exceed the subtask ceiling."""
        if num_subtasks > self.config.max_subtasks:
            raise GovernanceViolation(
                f"Decomposition produced {num_subtasks} subtasks — "
                f"governance ceiling is {self.config.max_subtasks}. "
                "Consolidate tasks or raise GovernanceConfig.max_subtasks."
            )
        if num_subtasks == 0:
            raise GovernanceViolation(
                "Decomposition produced 0 subtasks. Cannot orchestrate an empty plan."
            )

    # ── SLA enforcement ───────────────────────────────────────────────────────

    def should_slash(self, sla_breached: bool, status: str) -> bool:
        """Return True if the job should be slashed for SLA breach."""
        return (
            self.config.slash_on_sla_breach
            and sla_breached
            and status in ("Open", "InProgress")
        )

    # ── Introspection ─────────────────────────────────────────────────────────

    def summary(self) -> dict:
        return {
            "owner":                  self.config.owner,
            "verification_threshold": self.config.verification_threshold,
            "max_payment_usdc":       self.config.max_payment_usdc,
            "max_subtasks":           self.config.max_subtasks,
            "sla_seconds":            self.config.sla_seconds,
            "approved_capabilities":  self.config.approved_capabilities,
            "auto_release":           self.config.auto_release,
            "require_verification":   self.config.require_verification,
            "slash_on_sla_breach":    self.config.slash_on_sla_breach,
        }
