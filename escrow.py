"""
Brewing Escrow Engine
─────────────────────────────────────────────────────────────────────────────
Deterministic SLA-enforced escrow state machine.

Mirrors the on-chain Brewing Anchor program logic in pure Python for Swarms
integration. In production (SOLANA_MODE=1) this is replaced by BrewingClient
pointing at BsFiGxfJ9Spn5kp6bJoCxAwswKRskpTiPodNt8EA6QdM on Solana devnet.

State machine:
  OPEN → IN_PROGRESS → PENDING_RELEASE → COMPLETED
                     ↘ DISPUTED
  OPEN / IN_PROGRESS → SLASHED  (SLA breach)
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class JobStatus(Enum):
    OPEN            = "Open"
    IN_PROGRESS     = "InProgress"
    PENDING_RELEASE = "PendingRelease"
    COMPLETED       = "Completed"
    DISPUTED        = "Disputed"
    SLASHED         = "Slashed"


@dataclass
class EscrowJob:
    job_id:           str
    description:      str
    payment_usdc:     float
    capability:       str
    poster:           str
    sla_deadline_ts:  float              # Unix timestamp when SLA expires

    created_at:           float          = field(default_factory=time.time)
    status:               JobStatus      = JobStatus.OPEN
    worker:               Optional[str]  = None
    work_output:          Optional[str]  = None
    verification_score:   Optional[int]  = None
    accepted_at:          Optional[float] = None
    completed_at:         Optional[float] = None
    tx_signatures:        dict           = field(default_factory=dict)

    @property
    def sla_elapsed(self) -> float:
        return time.time() - self.created_at

    @property
    def sla_remaining(self) -> float:
        return max(0.0, self.sla_deadline_ts - time.time())

    @property
    def sla_breached(self) -> bool:
        return time.time() > self.sla_deadline_ts


class EscrowEngine:
    """
    In-process escrow engine with full SLA enforcement.

    Protocol constants mirror the Brewing Anchor program:
      - TREASURY_FEE_BPS = 250   (2.5% of every released payment)
      - VERIFICATION_THRESHOLD = 7  (minimum score to auto-release)
    """

    TREASURY_FEE_BPS:       int   = 250
    VERIFICATION_THRESHOLD: int   = 7
    DEFAULT_SLA_SECONDS:    int   = 300  # 5 minutes

    def __init__(self, verification_threshold: int = VERIFICATION_THRESHOLD) -> None:
        self._jobs:                   dict[str, EscrowJob] = {}
        self._collected_fees:         float                = 0.0
        self._verification_threshold: int                  = verification_threshold

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def post_job(
        self,
        description: str,
        payment_usdc: float,
        capability: str,
        poster: str = "orchestrator",
        sla_seconds: int = DEFAULT_SLA_SECONDS,
    ) -> EscrowJob:
        """Lock USDC in escrow and open job for worker assignment."""
        if payment_usdc <= 0:
            raise ValueError("payment_usdc must be > 0")
        job_id = str(uuid.uuid4())[:8].upper()
        job = EscrowJob(
            job_id=job_id,
            description=description,
            payment_usdc=payment_usdc,
            capability=capability,
            poster=poster,
            sla_deadline_ts=time.time() + sla_seconds,
        )
        self._jobs[job_id] = job
        job.tx_signatures["post"] = f"sim_post_{job_id}_escrow_locked"
        return job

    def accept_job(self, job_id: str, worker: str) -> EscrowJob:
        """Worker takes the job; SLA clock starts."""
        job = self._get(job_id)
        if job.status != JobStatus.OPEN:
            raise ValueError(f"Job {job_id} is {job.status.value}, cannot accept")
        if job.sla_breached:
            raise ValueError(f"Job {job_id} SLA already expired before acceptance")
        job.status      = JobStatus.IN_PROGRESS
        job.worker      = worker
        job.accepted_at = time.time()
        job.tx_signatures["accept"] = f"sim_accept_{job_id}_worker_{worker}"
        return job

    def submit_work(self, job_id: str, output: str, score: int) -> EscrowJob:
        """
        Worker submits deliverable; governed by verification threshold.
          score >= VERIFICATION_THRESHOLD  → PendingRelease
          score <  VERIFICATION_THRESHOLD  → Disputed (escrow held)
        """
        job = self._get(job_id)
        if job.status != JobStatus.IN_PROGRESS:
            raise ValueError(f"Job {job_id} is {job.status.value}, cannot submit")
        job.work_output        = output
        job.verification_score = score

        if score >= self._verification_threshold:
            job.status = JobStatus.PENDING_RELEASE
            job.tx_signatures["submit"] = f"sim_submit_{job_id}_score_{score}_PASS"
        else:
            job.status = JobStatus.DISPUTED
            job.tx_signatures["dispute"] = f"sim_dispute_{job_id}_score_{score}_FAIL"
        return job

    def release_payment(self, job_id: str) -> EscrowJob:
        """Release escrowed USDC to worker (2.5% fee retained by treasury)."""
        job = self._get(job_id)
        if job.status != JobStatus.PENDING_RELEASE:
            raise ValueError(f"Job {job_id} must be PendingRelease to release payment")
        fee = job.payment_usdc * (self.TREASURY_FEE_BPS / 10_000)
        self._collected_fees      += fee
        job.status                 = JobStatus.COMPLETED
        job.completed_at           = time.time()
        worker_receives            = job.payment_usdc - fee
        job.tx_signatures["release"] = (
            f"sim_release_{job_id}_worker_rcv_{worker_receives:.4f}USDC_"
            f"treasury_{fee:.4f}USDC"
        )
        return job

    def enforce_sla(self, job_id: str) -> EscrowJob:
        """
        Slash worker and reclaim full escrow after SLA breach.
        Maps to the Anchor program's `slash_job` instruction.
        """
        job = self._get(job_id)
        if not job.sla_breached:
            raise ValueError(f"SLA not yet expired for {job_id}")
        if job.status not in (JobStatus.IN_PROGRESS, JobStatus.OPEN):
            raise ValueError(f"Cannot slash job in {job.status.value} state")
        job.status = JobStatus.SLASHED
        job.tx_signatures["slash"] = (
            f"sim_slash_{job_id}_escrow_reclaimed_{job.payment_usdc}USDC"
        )
        return job

    # ── Queries ───────────────────────────────────────────────────────────────

    def get_job(self, job_id: str) -> EscrowJob:
        return self._get(job_id)

    def all_jobs(self) -> list[EscrowJob]:
        return list(self._jobs.values())

    def collected_fees(self) -> float:
        return self._collected_fees

    def open_jobs(self) -> list[EscrowJob]:
        return [j for j in self._jobs.values() if j.status == JobStatus.OPEN]

    def check_sla(self, job_id: str) -> tuple[bool, float]:
        """Returns (is_breached, seconds_remaining)."""
        job = self._get(job_id)
        return job.sla_breached, job.sla_remaining

    # ── Internal ──────────────────────────────────────────────────────────────

    def _get(self, job_id: str) -> EscrowJob:
        if job_id not in self._jobs:
            raise KeyError(f"Job {job_id} not found in escrow ledger")
        return self._jobs[job_id]
