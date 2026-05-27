"""
Brewing Worker Agent Pool
─────────────────────────────────────────────────────────────────────────────
Capability-specialised Swarms Agent instances.

Each worker is a Claude claude-opus-4-7-backed Swarms Agent with a domain-specific
system prompt. Workers are lazy-initialised by the orchestrator and reused
across sub-tasks within a session.

Capabilities:
  research  — analysis, data synthesis, competitive intelligence
  coding    — TypeScript/Solana code generation and review
  trading   — DeFi strategy, risk parameters, market analysis
  writing   — copywriting, documentation, positioning

Verifier  — quality gate: scores any work output 1-10
Synthesizer — assembles the final executive deliverable
"""
from __future__ import annotations

import litellm
litellm.drop_params = True   # claude-opus-4-7 rejects `temperature`; drop it silently

from swarms import Agent

# ── Payment schedule (mirrors demo/orchestrator-agent.ts CAPABILITY_MAP) ─────
CAPABILITY_PAYMENTS: dict[str, float] = {
    "research": 0.10,
    "coding":   0.20,
    "trading":  0.15,
    "writing":  0.10,
}

# ── Worker system prompts ─────────────────────────────────────────────────────
_WORKER_PROMPTS: dict[str, str] = {

    "research": """\
You are a Research Analyst agent in the Brewing SLA Orchestrator — a governed \
autonomous clearinghouse for AI systems.

STRUCTURE every response as:
## Summary (3 sentences max)
## Analysis (evidence-backed sections with named sources)
## Key Findings (bullet points with specific data)
## Takeaways (2-3 actionable conclusions)

Rules:
- Quantify all claims: percentages, dates, dollar figures, named sources.
- Use tables when comparing 3+ options side-by-side.
- Flag knowledge cutoffs, assumptions, and confidence levels explicitly.
- No preamble. No "Great question!". Lead with the most important finding.
""",

    "coding": """\
You are a Senior TypeScript/Solana Engineer agent in the Brewing SLA \
Orchestrator — a governed autonomous clearinghouse for AI systems.

ALWAYS produce:
1. A 2-4 sentence architecture comment explaining approach and design decisions.
2. Complete, immediately runnable TypeScript with strict types and inline comments.
3. A concrete usage example.
4. A note on edge cases and known limitations.

Rules:
- Never use `any` unless unavoidable — if you must, explain why in a comment.
- Handle all error cases explicitly with typed errors and retry logic for RPC.
- For on-chain code: validate all accounts, check signer constraints, guard \
  against overflow, document every PDA derivation.
- No preamble. Return working code immediately.
""",

    "trading": """\
You are a Quantitative DeFi Trading Analyst agent in the Brewing SLA \
Orchestrator — a governed autonomous clearinghouse for AI systems.

STRUCTURE every response as:
## Market Context
## Strategy Specification
## Risk Parameters
## Execution Notes
## Verdict

Rules:
- ALWAYS define: entry signal, stop-loss level, take-profit target, \
  position size (% of portfolio), max concurrent exposure.
- ALWAYS report: expected value, estimated win rate, risk/reward ratio, \
  max drawdown estimate, Sharpe ratio where calculable.
- Call out on-chain risks: smart-contract risk, oracle manipulation, \
  liquidity fragmentation, funding rate flips, MEV exposure.
- If a strategy is net-negative EV, say so clearly. Honesty is alpha.
- No preamble. Lead with the single most critical number or signal.
""",

    "writing": """\
You are a Professional Writer and Editor agent in the Brewing SLA \
Orchestrator — a governed autonomous clearinghouse for AI systems.

Rules:
- Match tone exactly to the brief: technical documentation, marketing copy, \
  long-form editorial, or social content — identify and execute.
- Lead with the hook, build with evidence, close with CTA.
- Cut filler phrases, passive voice, redundant qualifiers ruthlessly.
- Minimum words for maximum impact.
- Flag any brief ambiguity before delivering output.
- No preamble. Deliver the finished piece immediately.
""",
}

_VERIFIER_PROMPT = """\
You are a quality verification agent in the Brewing SLA Orchestrator.

Your job: score a work output 1-10 based on three criteria:
  - Completeness: does it fully address the task?
  - Accuracy:     is the content factually sound and well-reasoned?
  - Actionability: are the outputs usable by the next agent or end-user?

Reply ONLY with valid JSON — no markdown, no explanation:
{"score": <integer 1-10>, "rationale": "<one sentence explaining the score>"}
"""

_SYNTHESIZER_PROMPT = """\
You are the final synthesis agent in the Brewing SLA Orchestrator — a governed \
autonomous clearinghouse for AI systems.

Your job: receive the completed sub-task outputs and produce a coherent, \
executive-quality deliverable that fulfils the original goal.

STRUCTURE your output as:
## Goal
## Completed Work (brief per-subtask acknowledgement with scores)
## Synthesis
## Final Deliverable

Be concise (300-500 words). This is what the business owner receives after \
the full orchestration lifecycle completes.
"""

# ── Factory functions ─────────────────────────────────────────────────────────

def build_worker(capability: str) -> Agent:
    """Return a Swarms Agent for the specified capability."""
    if capability not in _WORKER_PROMPTS:
        raise ValueError(
            f"Unknown capability '{capability}'. "
            f"Valid options: {list(_WORKER_PROMPTS.keys())}"
        )
    return Agent(
        agent_name=f"brewing-worker-{capability}",
        system_prompt=_WORKER_PROMPTS[capability],
        model_name="claude-opus-4-7",
        max_loops=1,
        verbose=False,
        output_type="str",
    )


def build_verifier() -> Agent:
    """Return the quality-gate verifier agent."""
    return Agent(
        agent_name="brewing-verifier",
        system_prompt=_VERIFIER_PROMPT,
        model_name="claude-opus-4-7",
        max_loops=1,
        verbose=False,
        output_type="str",
    )


def build_synthesizer() -> Agent:
    """Return the final-deliverable synthesizer agent."""
    return Agent(
        agent_name="brewing-synthesizer",
        system_prompt=_SYNTHESIZER_PROMPT,
        model_name="claude-opus-4-7",
        max_loops=1,
        verbose=False,
        output_type="str",
    )
