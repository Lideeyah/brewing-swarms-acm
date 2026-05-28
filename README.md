# Brewing SLA Orchestrator

**Governed autonomous coordination and SLA enforcement agent for AI systems.**

Swarms ACM Hackathon · Frenzy Mode · [agent_card.json](agent_card.json)

---

## Core Thesis

Autonomous systems can coordinate intelligence. What they still lack is:

- **Accountability** — who is responsible when an agent delivers bad work?
- **Enforcement** — what stops a worker from collecting payment for a failed task?
- **Auditability** — how do you prove what happened, and in what order?
- **Settlement guarantees** — what ensures USDC moves only when the work passes?

Brewing governs autonomous execution through escrow-backed coordination workflows. Every task is scoped, delegated, verified, and settled by deterministic rules — without a human in the loop.

---

## Architecture

```
         User Request
              ↓
    ┌─────────────────────┐
    │  Brewing Orchestrator│  ← GovernanceEngine + EscrowEngine
    └─────────────────────┘
              ↓  decompose → validate → escrow lock
    ┌─────────────────────┐
    │  Specialist Agents  │  ← research · coding · trading · writing
    └─────────────────────┘
              ↓  execute task
    ┌─────────────────────┐
    │   Auditor Agent     │  ← independent verifier, scores 1–10
    └─────────────────────┘
              ↓
       score ≥ threshold?
        ↙             ↘
    Settle          Slash / Dispute
  USDC released   escrow held or reclaimed
```

---

## What it does

Brewing SLA Orchestrator accepts a natural-language goal and autonomously coordinates a team of specialist AI agents to achieve it — with SLA enforcement, escrow-backed payment settlement, and deterministic governance at every step.

```
goal → decompose → govern → escrow → delegate → verify → settle → synthesize
```

No human-in-the-loop. Every step is governed, auditable, and reversible.

---

## Execution flow

```
BrewingOrchestrator.run(goal)
  │
  ├─ 1. DECOMPOSE    Swarms Agent breaks goal into 2–4 sub-tasks (JSON plan)
  │
  ├─ 2. GOVERN       GovernanceEngine validates each task:
  │                    • capability approved?
  │                    • payment within cap?
  │                    • subtask count within ceiling?
  │
  ├─ 3. ESCROW       EscrowEngine.post_job()  ← USDC locked with SLA timer
  │
  ├─ 4. DELEGATE     Capability-specialised Swarms Agent executes:
  │                    research · coding · trading · writing
  │
  ├─ 5. VERIFY       brewing-verifier scores output 1–10 (independent agent)
  │
  ├─ 6. SETTLE       score ≥ threshold  →  EscrowEngine.release_payment()  ✅
  │                  score < threshold  →  EscrowEngine.dispute()           ⚠️
  │                  SLA breach         →  EscrowEngine.enforce_sla()       🔴
  │
  └─ 7. SYNTHESIZE   brewing-synthesizer assembles executive deliverable
```

---

## Governance flow

```
Task Submission
  → GovernanceEngine.validate_post()
      checks: capability allowlist · payment cap · subtask ceiling
  → EscrowEngine.post_job()
      USDC locked in escrow, SLA timer starts
  → Orchestrator delegates to specialist worker agent
  → Worker executes, delivers output
  → Auditor Agent (brewing-verifier) scores 1–10, independent of worker
  → GovernanceEngine.validate_release()
      score ≥ verification_threshold → release
      score <  verification_threshold → dispute
      time > sla_seconds + no completion → slash
  → EscrowEngine settles: payment released, held, or reclaimed
```

Every transition is logged with a simulated transaction signature. In `SOLANA_MODE=1`, each maps directly to an on-chain Anchor instruction.

---

## Swarms integration

Brewing is built natively on the Swarms multi-agent framework. Every agent in the pool is a `swarms.Agent` instance. The orchestrator itself implements the Swarms Agent interface and composes into any Swarms workflow.

**Orchestration model:**

- `BrewingOrchestrator` acts as the governing meta-agent
- It spawns and delegates to capability-specialist sub-agents: `brewing-worker-research`, `brewing-worker-coding`, `brewing-worker-trading`, `brewing-worker-writing`
- An independent `brewing-verifier` agent scores every output — it has no shared state with the worker that produced it
- `brewing-synthesizer` assembles the final deliverable from all passing sub-task outputs

**Autonomous delegation:** The orchestrator receives a natural-language goal, constructs a structured task plan via the decomposer agent, assigns each task to the right specialist, and routes the result through governance — without any human intervention between steps.

**Governed execution flows:** Every agent call is bounded by the `GovernanceEngine` before it runs and the `EscrowEngine` before it pays. No worker can collect payment outside the governed lifecycle.

```python
from swarms import SequentialWorkflow
from brewing_sla_orchestrator import BrewingOrchestrator

orchestrator = BrewingOrchestrator()
workflow = SequentialWorkflow(agents=[orchestrator])
workflow.run("Your multi-step goal here")
```

---

## Demo flows

### Happy path — full settlement

```
[10:42:01]  🧠  Decomposing goal into governed sub-tasks…
[10:42:03]      📋  2 sub-task(s): [research], [writing]

[10:42:03]  📬  Job #A1B2C3D4 [research] — 0.10 USDC escrowed  |  SLA 120s
[10:42:03]  🤝  worker-research accepted
[10:42:18]  🔍  verified: 8/10 — comprehensive analysis with cited sources
[10:42:18]  ✅  Completed  |  0.10 USDC released

[10:42:18]  📬  Job #E5F6G7H8 [writing] — 0.10 USDC escrowed  |  SLA 120s
[10:42:31]  🔍  verified: 9/10 — clear, compelling, on-brief
[10:42:31]  ✅  Completed  |  0.10 USDC released

  Settled 0.20 USDC  ·  Treasury 0.0050 USDC  ·  Disputed 0 job(s)
```

### Slash path — SLA breach

```
[10:45:00]  📬  Job #C3D4E5F6 [coding] — 0.20 USDC escrowed  |  SLA 120s
[10:47:01]  ⏰  SLA deadline exceeded (121s elapsed)
[10:47:01]  🔴  enforce_sla() → Job #C3D4E5F6 SLASHED — escrow reclaimed
```

### Dispute path — quality gate rejection

```
[10:48:00]  📬  Job #F6G7H8I9 [research] — 0.10 USDC escrowed
[10:49:30]  🔍  verified: 3/10 — insufficient depth, no cited sources
[10:49:30]  ⚠️  Score below threshold. Payment blocked → Disputed
             escrow held: 0.10 USDC
```

### Audit checkpoints

Every job carries a full audit trail:

```
sim_tx_post    = sim_post_A1B2C3D4_escrow_locked
sim_tx_release = sim_release_A1B2C3D4_worker_rcv_0.0975USDC_treasury_0.0025USDC
sim_tx_dispute = sim_dispute_F6G7H8I9_score_3_FAIL
sim_tx_slash   = sim_slash_C3D4E5F6_escrow_reclaimed_0.2USDC
```

In `SOLANA_MODE=1`, these are real on-chain transaction signatures.

---

## Agent pool

| Agent | Role | Model |
|---|---|---|
| `brewing-decomposer` | Goal → JSON sub-task plan | claude-opus-4-6 |
| `brewing-worker-research` | Analysis, data synthesis, competitive intel | claude-opus-4-6 |
| `brewing-worker-coding` | TypeScript/Solana code generation | claude-opus-4-6 |
| `brewing-worker-trading` | DeFi strategy, risk parameters | claude-opus-4-6 |
| `brewing-worker-writing` | Copywriting, docs, positioning | claude-opus-4-6 |
| `brewing-verifier` | Independent quality gate — scores 1–10 | claude-opus-4-6 |
| `brewing-synthesizer` | Final executive deliverable assembly | claude-opus-4-6 |

---

## Quick start

```bash
git clone https://github.com/Lideeyah/brewing-swarms-acm
cd brewing-swarms-acm
pip install -r requirements.txt
cp .env.example .env          # add your ANTHROPIC_API_KEY
python3 demo.py
```

Custom goal:

```bash
python3 demo.py "Research top DeFi yield strategies and write an investor brief"
```

Presenter script (narration cues + timing):

```bash
python3 demo_script.py
```

---

## Use as a Swarms agent

```python
from brewing_sla_orchestrator import BrewingOrchestrator

agent = BrewingOrchestrator()

# Drop-in Swarms Agent interface
result = agent.run(
    "Research autonomous agent coordination patterns, "
    "then write a developer positioning brief for Brewing"
)
print(result)
```

Compose into any Swarms workflow:

```python
from swarms import SequentialWorkflow
from brewing_sla_orchestrator import BrewingOrchestrator

orchestrator = BrewingOrchestrator()
workflow = SequentialWorkflow(agents=[orchestrator])
workflow.run("Your multi-step goal here")
```

---

## Governance

All execution is governed by deterministic rules — no surprises.

| Parameter | Default | Description |
|---|---|---|
| `verification_threshold` | `7/10` | Minimum quality score to release escrow |
| `max_payment_usdc` | `1.0` | Per-subtask payment cap |
| `max_subtasks` | `4` | Decomposition ceiling |
| `sla_seconds` | `300` | 5-minute SLA per sub-task |
| `auto_release` | `true` | Release payment without human approval |
| `slash_on_sla_breach` | `true` | Auto-slash workers who miss deadline |
| `treasury_fee_bps` | `250` | 2.5% protocol fee on every settlement |

Override at instantiation:

```python
from governance import GovernanceConfig
from brewing_sla_orchestrator import BrewingOrchestrator

config = GovernanceConfig(
    verification_threshold=8,   # stricter quality gate
    sla_seconds=600,            # 10-minute SLA
    max_payment_usdc=0.50,
)
agent = BrewingOrchestrator(governance_config=config)
```

---

## Escrow lifecycle

```
OPEN
 └─ accept_job()     → IN_PROGRESS
     ├─ submit_work() (score ≥ threshold)  → PENDING_RELEASE → COMPLETED  ✅
     ├─ submit_work() (score < threshold)  → DISPUTED                      ⚠️
     └─ sla_breach + enforce_sla()         → SLASHED                       🔴
```

The escrow engine runs in-process by default (simulation). Set `SOLANA_MODE=1`
to route through the deployed Brewing Anchor program on Solana devnet:

```
Program  : BsFiGxfJ9Spn5kp6bJoCxAwswKRskpTiPodNt8EA6QdM
USDC Mint: 4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU
```

---

## Demo output (example)

```
╔══════════════════════════════════════════════════════════════════════╗
║  BREWING SLA ORCHESTRATOR  ·  Swarms ACM Demo                        ║
║  Governed Autonomous Clearinghouse for AI Systems                    ║
╠══════════════════════════════════════════════════════════════════════╣
║  Framework  : Swarms multi-agent (claude-opus-4-6)                   ║
║  Escrow     : Simulated  (SOLANA_MODE=1 for live on-chain)           ║
║  Mode       : Frenzy — deterministic, reproducible                   ║
╚══════════════════════════════════════════════════════════════════════╝

  GOAL
  ──────────────────────────────────────────────────────────────────
  Research autonomous AI agent coordination patterns and write a
  200-word positioning brief for Brewing SLA Orchestrator.
  ──────────────────────────────────────────────────────────────────

[10:42:01]  🧠  Decomposing goal into governed sub-tasks…
[10:42:03]      📋  2 sub-task(s) identified:
                    1. [research] Identify and compare leading frameworks
                    2. [writing]  Write positioning brief for Brewing

[10:42:03]  📬  Job #A1B2C3D4 [research] — 0.10 USDC escrowed  |  SLA 120s
[10:42:03]  🤝  #A1B2C3D4 — worker-research accepted
[10:42:03]  ⚙️   #A1B2C3D4 [research] executing…
[10:42:18]  🔍  #A1B2C3D4 verified: 8/10 — comprehensive analysis with cited sources
[10:42:18]  ✅  #A1B2C3D4 [research] — Completed (score 8/10)  |  0.10 USDC released

[10:42:18]  📬  Job #E5F6G7H8 [writing] — 0.10 USDC escrowed   |  SLA 120s
[10:42:18]  🤝  #E5F6G7H8 — worker-writing accepted
[10:42:18]  ⚙️   #E5F6G7H8 [writing] executing…
[10:42:31]  🔍  #E5F6G7H8 verified: 9/10 — clear, compelling, on-brief
[10:42:31]  ✅  #E5F6G7H8 [writing] — Completed (score 9/10)   |  0.10 USDC released

[10:42:31]  🔬  Synthesizing final deliverable…

──────────────────────────────────────────────────────────────────────
  ORCHESTRATOR RESULT
──────────────────────────────────────────────────────────────────────

  COMPLETED WORK
  ✅  [RESEARCH]   #A1B2C3D4  8/10  Framework comparison: Swarms, AutoGen, CrewAI
  ✅  [WRITING]    #E5F6G7H8  9/10  200-word positioning brief

  ┌───────────────────────── FINAL DELIVERABLE ──────────────────────┐
  │                                                                   │
  │  Brewing SLA Orchestrator stands apart from AutoGen and CrewAI   │
  │  by combining governed execution with on-chain escrow settlement  │
  │  — the first autonomous clearinghouse with enforceable SLAs.     │
  │                                                                   │
  └───────────────────────────────────────────────────────────────────┘

──────────────────────────────────────────────────────────────────────
  ESCROW LEDGER
──────────────────────────────────────────────────────────────────────

  JOB ID        TYPE          SCORE    STATUS            PAYMENT
  ────────────  ────────────  ───────  ────────────────  ────────────
  #A1B2C3D4     research      8/10     Completed         0.1000 USDC  ✅
  #E5F6G7H8     writing       9/10     Completed         0.1000 USDC  ✅
  ────────────  ────────────  ───────  ────────────────  ────────────

  Settled 0.2000 USDC   ·   Treasury 0.0050 USDC   ·   Disputed 0 job(s)
```

---

## Frenzy Mode · Tokenization

Brewing is submitted under **Frenzy Mode** for the Swarms ACM hackathon.

| Field | Value |
|---|---|
| Ticker | `BREW` |
| Category | Governed autonomous coordination infrastructure |
| Marketplace | Swarms agent marketplace — callable via `.run()` |
| Agent card | [`agent_card.json`](agent_card.json) |
| Submission mode | `frenzy` |

The `BREW` token represents access to and governance participation in the Brewing SLA Orchestrator clearinghouse. Escrow settlement, SLA enforcement, and treasury fee collection are the protocol's economic primitives. The architecture is designed to tokenize the coordination layer itself — governed execution as an on-chain primitive.

---

## Architecture

```
brewing-swarms-acm/
├── brewing_sla_orchestrator.py   ← Main agent  (Swarms ACM entry point)
├── escrow.py                     ← SLA escrow state machine
├── governance.py                 ← Deterministic access-control rules
├── workers.py                    ← Swarms Agent factory (6 agents)
├── demo.py                       ← Demo runner
├── demo_script.py                ← Presenter narration script
├── agent_card.json               ← Swarms marketplace listing metadata
├── requirements.txt
└── .env.example
```

---

## On-chain foundation

The escrow engine mirrors the deployed Brewing Anchor program (Solana devnet).
Every state transition has a corresponding on-chain instruction:

| Engine call | On-chain instruction |
|---|---|
| `post_job()` | `create_job` — locks USDC in PDA escrow |
| `accept_job()` | `accept_job` — worker commits, SLA starts |
| `submit_work()` | `complete_job` — submits deliverable hash |
| `release_payment()` | `release_payment` — transfers USDC to worker |
| `enforce_sla()` | `slash_job` — reclaims escrow on SLA breach |

---

## Environment

```
ANTHROPIC_API_KEY   required — Claude API key
```

<details>
<summary>On-chain mode (optional)</summary>

Set `SOLANA_MODE=1` to route escrow through the deployed Anchor program on Solana devnet instead of the in-process simulation.

```
SOLANA_MODE         1
RPC_URL             Solana RPC endpoint
POSTER_SECRET_KEY   Solana keypair JSON array
```

Program: `BsFiGxfJ9Spn5kp6bJoCxAwswKRskpTiPodNt8EA6QdM`

</details>

---

## License

MIT
