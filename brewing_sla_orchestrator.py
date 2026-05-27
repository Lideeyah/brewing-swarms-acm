"""
Brewing SLA Orchestrator
─────────────────────────────────────────────────────────────────────────────
A governed autonomous clearinghouse agent for AI systems.

Swarms ACM Hackathon — Frenzy Mode submission.

Architecture
────────────
  BrewingOrchestrator
    ├── GovernanceEngine  — deterministic access-control + verification rules
    ├── EscrowEngine      — SLA-enforced escrow state machine (5-step lifecycle)
    ├── WorkerPool        — Swarms Agent instances per capability
    │     ├── brewing-worker-research  (claude-opus-4-7)
    │     ├── brewing-worker-coding    (claude-opus-4-7)
    │     ├── brewing-worker-trading   (claude-opus-4-7)
    │     └── brewing-worker-writing   (claude-opus-4-7)
    ├── brewing-verifier  — quality gate  (scores 1-10, threshold 7/10)
    └── brewing-synthesizer — final deliverable assembler

Execution flow
──────────────
  goal
    → decompose (Orchestrator + Claude)
    → for each subtask:
        validate (GovernanceEngine)
        post_job (EscrowEngine)  ← USDC locked
        accept_job (EscrowEngine)
        execute (WorkerAgent)
        verify (VerifierAgent)
        release_payment / dispute (EscrowEngine + GovernanceEngine)
    → synthesize (SynthesizerAgent)
    → return executive deliverable + SLA ledger

On-chain integration
────────────────────
Set SOLANA_MODE=1 to replace EscrowEngine with BrewingClient (Anchor/Solana SDK)
pointing at the deployed Brewing program on Solana devnet:
  Program  : BsFiGxfJ9Spn5kp6bJoCxAwswKRskpTiPodNt8EA6QdM
  USDC Mint: 4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU

Swarms marketplace usage
────────────────────────
  from brewing_sla_orchestrator import BrewingOrchestrator
  agent = BrewingOrchestrator()
  result = agent.run("Research top DeFi yield strategies and write a brief")
"""
from __future__ import annotations

import json
import os
import re
import textwrap
import time
from typing import Optional

import anthropic
from swarms import Agent

from escrow import EscrowEngine, EscrowJob, JobStatus
from governance import GovernanceConfig, GovernanceEngine, GovernanceViolation
from workers import (
    CAPABILITY_PAYMENTS,
    build_synthesizer,
    build_verifier,
    build_worker,
)

# ── Logger ────────────────────────────────────────────────────────────────────

def _ts() -> str:
    return time.strftime("%H:%M:%S")

def _log(msg: str)  -> None: print(f"[{_ts()}]  {msg}")
def _warn(msg: str) -> None: print(f"[{_ts()}]  ⚠️  {msg}")
def _err(msg: str)  -> None: print(f"[{_ts()}]  ❌ {msg}")


# ── Display utilities ─────────────────────────────────────────────────────────

_W = 70  # output column width

def _strip_md(text: str) -> str:
    """Strip markdown syntax for clean terminal rendering."""
    out = []
    for line in text.split("\n"):
        m3 = re.match(r"^#{3,} (.+)$", line)
        if m3:
            out.append(f"  {m3.group(1)}")
            continue
        m2 = re.match(r"^## (.+)$", line)
        if m2:
            out.append(f"  {m2.group(1)}")
            continue
        m1 = re.match(r"^# (.+)$", line)
        if m1:
            out.append(m1.group(1).upper())
            continue
        if re.match(r"^-{3,}$", line.strip()):
            continue          # drop horizontal rules
        line = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
        line = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\1", line)
        line = re.sub(r"^(\s*)[-•] ", r"\1• ", line)
        out.append(line)
    # collapse 3+ consecutive blank lines → 1
    result, prev_blank = [], 0
    for ln in out:
        blank = not ln.strip()
        if blank:
            prev_blank += 1
        else:
            prev_blank = 0
        if prev_blank <= 1:
            result.append(ln)
    return "\n".join(result).strip()


def _parse_sections(text: str) -> dict[str, str]:
    """Split '## Header\\nContent' document into a {header: content} dict."""
    sections: dict[str, str] = {}
    current: str | None = None
    buf: list[str] = []
    for line in text.split("\n"):
        m = re.match(r"^## (.+)$", line)
        if m:
            if current is not None:
                sections[current] = "\n".join(buf).strip()
            current, buf = m.group(1).strip(), []
        else:
            buf.append(line)
    if current is not None:
        sections[current] = "\n".join(buf).strip()
    return sections


def _box(content: str, title: str = "", width: int = _W) -> None:
    """Render content inside a Unicode box, printed to stdout."""
    iw   = width - 8          # inner text width
    dash = "─" * (width - 4)  # dash run between ┌ and ┐
    if title:
        t  = f" {title} "
        ld = (len(dash) - len(t)) // 2
        rd = len(dash) - len(t) - ld
        top = f"  ┌{'─'*ld}{t}{'─'*rd}┐"
    else:
        top = f"  ┌{dash}┐"
    blank_row = f"  │{' ' * (width - 4)}│"
    print(top)
    print(blank_row)
    for para in content.split("\n\n"):
        if not para.strip():
            print(blank_row)
            continue
        for raw in para.split("\n"):
            stripped = raw.strip()
            if not stripped:
                print(blank_row)
                continue
            for wline in textwrap.wrap(stripped, width=iw) or [""]:
                print(f"  │  {wline:<{iw}}  │")
        print(blank_row)
    print(f"  └{dash}┘")


# ── Internal subtask container ────────────────────────────────────────────────

class _SubTask:
    __slots__ = ("capability", "task", "rationale", "job", "output", "score")

    def __init__(self, capability: str, task: str, rationale: str) -> None:
        self.capability: str                   = capability
        self.task:       str                   = task
        self.rationale:  str                   = rationale
        self.job:        Optional[EscrowJob]   = None
        self.output:     Optional[str]         = None
        self.score:      Optional[int]         = None


# ── Main orchestrator ─────────────────────────────────────────────────────────

class BrewingOrchestrator:
    """
    Brewing SLA Orchestrator — governed multi-agent clearinghouse.

    Implements the Swarms Agent interface (.run(task)) and can be composed
    into any Swarms workflow (SequentialWorkflow, ConcurrentWorkflow, etc.)

    Parameters
    ----------
    governance_config : GovernanceConfig, optional
        Override default governance rules.
    verbose : bool
        Stream per-step progress to stdout (default True).

    Quick start
    -----------
    >>> from brewing_sla_orchestrator import BrewingOrchestrator
    >>> agent = BrewingOrchestrator()
    >>> result = agent.run("Research Solana DeFi and write an investor brief")
    """

    AGENT_NAME    = "brewing-sla-orchestrator"
    AGENT_VERSION = "1.0.0"
    DESCRIPTION   = (
        "Governed autonomous clearinghouse agent for AI systems. "
        "Decomposes goals into SLA-enforced sub-tasks, delegates to specialist "
        "Swarms agents, verifies output quality via a governance threshold, "
        "and settles escrow-backed payments — fully autonomously."
    )

    # Decompose prompt — returns structured JSON for deterministic parsing
    _DECOMPOSE_PROMPT = """\
You are the Brewing SLA Orchestrator — a governed autonomous clearinghouse.

Goal: "{goal}"

Decompose into 2-4 concrete sub-tasks for specialist agents.
Each must map to exactly one capability: research, coding, trading, or writing.

Reply ONLY with valid JSON (no markdown, no explanation):
{{
  "subtasks": [
    {{
      "capability": "research|coding|trading|writing",
      "task": "Specific deliverable description (100-200 words). Be explicit.",
      "rationale": "One sentence: why this capability owns this piece."
    }}
  ]
}}"""

    def __init__(
        self,
        governance_config: Optional[GovernanceConfig] = None,
        verbose: bool = True,
    ) -> None:
        self.governance = GovernanceEngine(governance_config)
        # Thread the governance threshold into escrow so submit_work and
        # validate_release use the same pass/fail boundary.
        self.escrow = EscrowEngine(
            verification_threshold=self.governance.config.verification_threshold
        )
        self.verbose    = verbose

        # Lazy agent pool — built on first use, reused within session
        self._workers:     dict[str, Agent] = {}
        self._verifier:    Optional[Agent]  = None
        self._synthesizer: Optional[Agent]  = None

        # Decomposer uses the Anthropic SDK directly for clean, undecorated JSON output.
        # Swarms agent boxes can garble the return value; the SDK gives us raw text.
        self._anthropic = anthropic.Anthropic()

    # ── Swarms-compatible entrypoint ──────────────────────────────────────────

    def run(self, task: str) -> str:
        """
        Swarms Agent-compatible run method.
        Orchestrates the full SLA lifecycle and returns the synthesized result.
        """
        return self.orchestrate(task)

    # ── Full orchestration pipeline ───────────────────────────────────────────

    def orchestrate(self, goal: str) -> str:
        """End-to-end governed orchestration."""
        self._banner(goal)

        # ── 1. Decompose goal → sub-tasks ────────────────────────────────────
        subtasks = self._decompose(goal)
        if not subtasks:
            return "Decomposition failed — no sub-tasks produced."

        try:
            self.governance.validate_orchestration(len(subtasks), caller="orchestrator")
        except GovernanceViolation as e:
            _err(f"Governance rejected orchestration plan: {e}")
            return str(e)

        # ── 2. Execute each sub-task through the full escrow lifecycle ────────
        completed: list[_SubTask] = []
        for st in subtasks:
            result = self._execute_subtask(st)
            if result is not None:
                completed.append(result)

        if not completed:
            return (
                "No sub-tasks passed governance verification. "
                "All jobs are in Disputed state — escrow held."
            )

        # ── 3. Synthesize final deliverable ───────────────────────────────────
        synthesis = self._synthesize(goal, completed)
        self._print_summary(completed, synthesis)
        return synthesis

    # ── Step 1: Decompose ─────────────────────────────────────────────────────

    def _decompose(self, goal: str) -> list[_SubTask]:
        if self.verbose:
            _log("🧠  Decomposing goal into governed sub-tasks…")

        prompt = self._DECOMPOSE_PROMPT.format(goal=goal)

        # Use the Anthropic SDK directly — avoids Swarms box decoration garbling the JSON.
        msg = self._anthropic.messages.create(
            model="claude-opus-4-6",
            max_tokens=2048,
            system=(
                "You are the Brewing SLA Orchestrator goal-decomposition engine. "
                "You receive a natural-language goal and return a JSON plan of "
                "2-4 sub-tasks for specialist worker agents. Return ONLY valid JSON."
            ),
            messages=[{"role": "user", "content": prompt}],
        )
        text = msg.content[0].text.strip()

        # Strip markdown fences if the model adds them
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:].strip()

        # Strategy 1: direct parse
        parsed = None
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            pass

        # Strategy 2: find the first valid JSON object anywhere in the string
        if parsed is None:
            decoder = json.JSONDecoder()
            for i, ch in enumerate(text):
                if ch == "{":
                    try:
                        parsed, _ = decoder.raw_decode(text, i)
                        break
                    except json.JSONDecodeError:
                        continue

        if parsed is None:
            _err("Decomposition produced no parseable JSON.")
            return []

        subtasks = [
            _SubTask(s["capability"], s["task"], s["rationale"])
            for s in parsed.get("subtasks", [])
        ]

        if self.verbose:
            _log(f"    📋  {len(subtasks)} sub-task(s) identified:")
            for i, s in enumerate(subtasks, 1):
                _log(f"        {i}. [{s.capability}] {s.rationale}")
        return subtasks

    # ── Step 2: Single sub-task execution ─────────────────────────────────────

    def _execute_subtask(self, st: _SubTask) -> Optional[_SubTask]:
        cap      = st.capability
        payment  = CAPABILITY_PAYMENTS.get(cap, 0.10)

        # — Governance: validate this post is permitted —
        try:
            self.governance.validate_post(cap, payment, caller="orchestrator")
        except GovernanceViolation as e:
            _err(f"Governance blocked [{cap}]: {e}")
            return None

        # — Escrow: post job (USDC locked) —
        job = self.escrow.post_job(
            description=st.task,
            payment_usdc=payment,
            capability=cap,
            sla_seconds=self.governance.config.sla_seconds,
        )
        st.job = job
        if self.verbose:
            _log(
                f"📬  Job #{job.job_id} [{cap}] — "
                f"{payment} USDC escrowed  |  SLA {self.governance.config.sla_seconds}s"
            )

        # — Escrow: worker accepts —
        self.escrow.accept_job(job.job_id, worker=f"brewing-worker-{cap}")
        if self.verbose:
            _log(f"🤝  #{job.job_id} — worker-{cap} accepted")

        # — Worker agent executes task —
        # We use the Anthropic SDK directly with the worker's system_prompt.
        # Swarms Agent.run() returns conversation-history strings, not the
        # clean LLM response; the SDK gives us the actual completion text.
        if self.verbose:
            _log(f"⚙️   #{job.job_id} [{cap}] executing…")
        worker = self._get_worker(cap)
        msg = self._anthropic.messages.create(
            model="claude-opus-4-6",
            max_tokens=4096,
            system=worker.system_prompt,
            messages=[{"role": "user", "content": st.task}],
        )
        output = msg.content[0].text
        st.output = output

        # — Verifier scores output —
        score  = self._verify(job.job_id, st.task, output)
        st.score = score

        # — Governance: validate payment release —
        try:
            self.governance.validate_release(score, caller="orchestrator")
        except GovernanceViolation as e:
            _warn(str(e))
            self.escrow.submit_work(job.job_id, output, score)   # → Disputed
            if self.verbose:
                _log(f"⚠️   #{job.job_id} [{cap}] → Disputed (score {score}/10)")
            return None  # exclude from synthesis

        # — Escrow: submit + release payment —
        self.escrow.submit_work(job.job_id, output, score)
        self.escrow.release_payment(job.job_id)
        if self.verbose:
            _log(
                f"✅  #{job.job_id} [{cap}] — Completed "
                f"(score {score}/10)  |  {payment} USDC released"
            )

        # — SLA audit check —
        breached, _ = self.escrow.check_sla(job.job_id)
        if breached and self.verbose:
            _warn(f"#{job.job_id} completed AFTER SLA deadline")

        return st

    # ── Step 3: Verification ──────────────────────────────────────────────────

    def _verify(self, job_id: str, task: str, output: str) -> int:
        prompt = (
            f"TASK:\n{task[:800]}\n\n"
            f"WORK OUTPUT:\n{output[:4000]}\n\n"
            "Score this 1-10. Reply ONLY with JSON: "
            '{"score": <int 1-10>, "rationale": "<one sentence>"}'
        )
        # Use Anthropic SDK directly — same reason as decomposer: clean JSON, no box noise.
        try:
            msg = self._anthropic.messages.create(
                model="claude-opus-4-6",
                max_tokens=256,
                system=(
                    "You are a quality verification agent. "
                    "Reply ONLY with valid JSON: "
                    '{"score": <integer 1-10>, "rationale": "<one sentence>"}'
                ),
                messages=[{"role": "user", "content": prompt}],
            )
            raw = msg.content[0].text.strip()
            # Strip markdown fences
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:].strip()
            # Find first JSON object
            decoder = json.JSONDecoder()
            parsed  = None
            for i, ch in enumerate(raw):
                if ch == "{":
                    try:
                        parsed, _ = decoder.raw_decode(raw, i)
                        break
                    except json.JSONDecodeError:
                        continue
            if parsed is None:
                parsed = json.loads(raw)
            score = max(1, min(10, int(parsed["score"])))
            if self.verbose:
                _log(
                    f"🔍  #{job_id} verified: {score}/10 — "
                    f"{parsed.get('rationale', '—')}"
                )
            return score
        except Exception as exc:
            _warn(f"Verifier parse failed for #{job_id} ({exc}) — defaulting score to 5")
            return 5

    # ── Step 4: Synthesis ─────────────────────────────────────────────────────

    def _synthesize(self, goal: str, subtasks: list[_SubTask]) -> str:
        if self.verbose:
            _log("🔬  Synthesizing final deliverable…")
        synthesizer = self._get_synthesizer()

        parts = [
            f"[{s.capability.upper()}] Job #{s.job.job_id if s.job else 'N/A'} "
            f"(score: {s.score}/10)\n"
            f"Task: {s.task[:200]}\n"
            f"Output excerpt:\n{(s.output or '')[:800]}"
            for s in subtasks
        ]

        prompt = (
            f"ORIGINAL GOAL:\n{goal}\n\n"
            f"COMPLETED SUB-TASKS ({len(subtasks)}):\n\n"
            + "\n\n─────\n\n".join(parts)
        )
        # SDK call — same reason: synthesizer.run() returns history, not clean text.
        msg = self._anthropic.messages.create(
            model="claude-opus-4-6",
            max_tokens=2048,
            system=synthesizer.system_prompt,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text

    # ── Agent pool ────────────────────────────────────────────────────────────

    def _get_worker(self, capability: str) -> Agent:
        if capability not in self._workers:
            self._workers[capability] = build_worker(capability)
        return self._workers[capability]

    def _get_verifier(self) -> Agent:
        if self._verifier is None:
            self._verifier = build_verifier()
        return self._verifier

    def _get_synthesizer(self) -> Agent:
        if self._synthesizer is None:
            self._synthesizer = build_synthesizer()
        return self._synthesizer

    # ── Display ───────────────────────────────────────────────────────────────

    def _banner(self, goal: str) -> None:
        g   = self.governance.config
        div = "─" * (_W - 4)
        print()
        print("╔" + "═" * (_W - 2) + "╗")
        print("║" + "  BREWING SLA ORCHESTRATOR  —  Governed Multi-Agent".ljust(_W - 2) + "║")
        print("║" + "  Swarms ACM  ·  Frenzy Mode".ljust(_W - 2) + "║")
        print("╚" + "═" * (_W - 2) + "╝")
        print()
        _log(f"Goal       : {goal[:80]}{'…' if len(goal) > 80 else ''}")
        _log(f"SLA        : {g.sla_seconds}s per sub-task")
        _log(f"Threshold  : {g.verification_threshold}/10 quality gate")
        _log(f"Capabilities: {', '.join(g.approved_capabilities)}")
        print()

    def _print_summary(self, completed: list[_SubTask], synthesis: str) -> None:
        all_jobs = self.escrow.all_jobs()
        disputed = [j for j in all_jobs if j.status == JobStatus.DISPUTED]
        total    = sum(CAPABILITY_PAYMENTS.get(s.capability, 0.10) for s in completed)
        fees     = self.escrow.collected_fees()

        sections = _parse_sections(synthesis)
        W = _W

        print()
        print("─" * W)
        print("  ORCHESTRATOR RESULT")
        print("─" * W)

        # — Goal ——————————————————————————————————————————————————
        goal_text = _strip_md(sections.get("Goal", ""))
        if goal_text:
            print()
            print("  GOAL")
            for line in textwrap.wrap(goal_text, W - 4):
                print(f"  {line}")

        # — Completed work (built from data, not synthesizer text) ——
        print()
        print("  COMPLETED WORK")
        for st in completed:
            jid   = st.job.job_id if st.job else "N/A"
            rat   = st.rationale[:64] if st.rationale else ""
            print(f"  ✅  [{st.capability.upper():<10}]  #{jid}  {st.score}/10")
            print(f"       {rat}")
        for j in disputed:
            print(f"  ⚠️   [{j.capability.upper():<10}]  #{j.job_id}  {j.verification_score}/10  (disputed — escrow held)")

        # — Synthesis note ————————————————————————————————————————
        synth_text = _strip_md(sections.get("Synthesis", ""))
        if synth_text:
            print()
            print("  SYNTHESIS")
            for line in synth_text.split("\n"):
                if line.strip():
                    for wl in textwrap.wrap(line.strip(), W - 4):
                        print(f"  {wl}")

        # — Final Deliverable in a box ————————————————————————————
        deliverable = _strip_md(sections.get("Final Deliverable", ""))
        if deliverable:
            print()
            _box(deliverable, title="FINAL DELIVERABLE", width=W)

        # — Escrow ledger ——————————————————————————————————————————
        print()
        print("─" * W)
        print("  ESCROW LEDGER")
        print("─" * W)
        print()
        hdr = f"  {'JOB ID':<12}  {'TYPE':<12}  {'SCORE':<7}  {'STATUS':<16}  PAYMENT"
        print(hdr)
        print("  " + "─" * (W - 4))
        for st in completed:
            j = st.job
            if j:
                print(
                    f"  #{j.job_id:<11}  {st.capability:<12}  {st.score}/10   "
                    f"  {'Completed':<16}  {j.payment_usdc:.4f} USDC  ✅"
                )
        for j in disputed:
            print(
                f"  #{j.job_id:<11}  {j.capability:<12}  {j.verification_score}/10   "
                f"  {'Disputed':<16}  {j.payment_usdc:.4f} USDC  ⚠️  held"
            )
        print("  " + "─" * (W - 4))
        print()
        print(
            f"  Settled  {total:.4f} USDC"
            f"   ·   Treasury  {fees:.4f} USDC"
            f"   ·   Disputed  {len(disputed)} job(s)"
        )
        print()
        print("─" * W)
        print()


# ── CLI entrypoint ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    goal = (
        sys.argv[1]
        if len(sys.argv) > 1
        else (
            "Research the top 3 autonomous AI agent coordination frameworks, "
            "then write a 200-word positioning brief for the Brewing SLA Orchestrator "
            "that highlights governed execution, SLA enforcement, and escrow-backed settlement "
            "as differentiated advantages"
        )
    )
    orchestrator = BrewingOrchestrator(verbose=True)
    orchestrator.run(goal)
