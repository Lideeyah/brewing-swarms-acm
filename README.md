# Brewing SLA Orchestrator

**Governed autonomous clearinghouse agent for AI systems.**

Swarms ACM Hackathon · Frenzy Mode · [agent_card.json](agent_card.json)

---

## What it does

Brewing SLA Orchestrator is a multi-agent system that accepts a natural-language goal and autonomously coordinates a team of specialist AI agents to achieve it — with SLA enforcement, escrow-backed payment settlement, and deterministic governance at every step.

```
goal → decompose → delegate → verify → settle → synthesize
```

No human-in-the-loop. Every step is governed, auditable, and reversible.

---

## Execution flow

```
BrewingOrchestrator.run(goal)
  │
  ├─ 1. DECOMPOSE    Swarms Agent breaks goal into 2-4 sub-tasks (JSON plan)
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
  ├─ 5. VERIFY       brewing-verifier scores output 1-10
  │
  ├─ 6. SETTLE       score ≥ 7  →  EscrowEngine.release_payment()  ✅
  │                  score < 7  →  EscrowEngine.dispute()           ⚠️  (escrow held)
  │
  └─ 7. SYNTHESIZE   brewing-synthesizer assembles executive deliverable
```

---

## Agent pool

| Agent | Role | Model |
|---|---|---|
| `brewing-decomposer` | Goal → JSON sub-task plan | claude-opus-4-7 |
| `brewing-worker-research` | Analysis, data synthesis, competitive intel | claude-opus-4-7 |
| `brewing-worker-coding` | TypeScript/Solana code generation | claude-opus-4-7 |
| `brewing-worker-trading` | DeFi strategy, risk parameters | claude-opus-4-7 |
| `brewing-worker-writing` | Copywriting, docs, positioning | claude-opus-4-7 |
| `brewing-verifier` | Quality gate — scores 1-10, threshold 7/10 | claude-opus-4-7 |
| `brewing-synthesizer` | Final executive deliverable assembly | claude-opus-4-7 |

---

## Quick start

```bash
git clone https://github.com/Lideeyah/brewing-swarms-acm
cd brewing-swarms-acm
pip install -r requirements.txt
cp .env.example .env          # add your ANTHROPIC_API_KEY
python demo.py
```

Custom goal:

```bash
python demo.py "Research top DeFi yield strategies and write an investor brief"
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
     ├─ submit_work() (score ≥ 7)  → PENDING_RELEASE → COMPLETED  ✅
     ├─ submit_work() (score < 7)  → DISPUTED                      ⚠️
     └─ sla_breach + enforce_sla() → SLASHED                       🔴
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
╔══════════════════════════════════════════════════════════════════╗
║     BREWING SLA ORCHESTRATOR  —  Governed Multi-Agent           ║
║     Swarms ACM  ·  Frenzy Mode                                  ║
╚══════════════════════════════════════════════════════════════════╝

[10:42:01]  Goal       : Research autonomous AI agent frameworks...
[10:42:01]  SLA        : 120s per sub-task
[10:42:01]  Threshold  : 6/10 quality gate

[10:42:01]  🧠  Decomposing goal into governed sub-tasks…
[10:42:03]      📋  2 sub-task(s) identified:
[10:42:03]          1. [research] Identify and compare leading frameworks
[10:42:03]          2. [writing]  Write positioning brief for Brewing

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

═══════════════════════ ORCHESTRATOR RESULT ═══════════════════════

## Goal
Research autonomous AI agent coordination patterns and write a positioning brief.

## Completed Work
- [RESEARCH] #A1B2C3D4 (8/10): Framework comparison across Swarms, AutoGen, CrewAI
- [WRITING]  #E5F6G7H8 (9/10): 200-word positioning brief

## Final Deliverable
Brewing SLA Orchestrator stands apart from AutoGen and CrewAI by combining
governed execution with on-chain escrow settlement...

════════════════════════ ESCROW LEDGER ════════════════════════════
  #A1B2C3D4  [research  ]  score=8/10  status=Completed          payment=0.1 USDC
  #E5F6G7H8  [writing   ]  score=9/10  status=Completed          payment=0.1 USDC

  Settled : 0.20 USDC  |  Treasury fees : 0.0050 USDC  |  Disputed : 0 job(s)
═══════════════════════════════════════════════════════════════════
```

---

## Architecture

```
brewing-swarms-acm/
├── brewing_sla_orchestrator.py   ← Main agent  (Swarms ACM entry point)
├── escrow.py                     ← SLA escrow state machine
├── governance.py                 ← Deterministic access-control rules
├── workers.py                    ← Swarms Agent factory (6 agents)
├── demo.py                       ← Deterministic demo (run instantly)
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
SOLANA_MODE         0 (default simulation) | 1 (live Solana devnet)
RPC_URL             Solana RPC (only for SOLANA_MODE=1)
POSTER_SECRET_KEY   Solana keypair JSON array (only for SOLANA_MODE=1)
```

---

## License

MIT
