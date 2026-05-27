"""
Brewing SLA Orchestrator — Presenter Script
─────────────────────────────────────────────────────────────────────────────
Run this for a formatted narration guide before going live.

  python3 demo_script.py

Then in a separate terminal:
  python3 demo.py
"""

W = 70

def rule(char="─"):
    print(char * W)

def section(title):
    print()
    rule("═")
    print(f"  {title}")
    rule("═")
    print()

def cue(label, text):
    print(f"  [{label}]")
    import textwrap
    for line in textwrap.wrap(text, W - 6):
        print(f"        {line}")
    print()

def say(text):
    import textwrap
    print("  SAY:")
    for line in textwrap.wrap(f'"{text}"', W - 8):
        print(f"        {line}")
    print()

def show(text):
    print(f"  SHOW:   {text}")
    print()

def cmd(text):
    print(f"  TYPE:   {text}")
    print()

def point(text):
    print(f"  POINT:  {text}")
    print()

def tip(text):
    import textwrap
    print("  TIP:")
    for line in textwrap.wrap(text, W - 8):
        print(f"        {line}")
    print()


# ─────────────────────────────────────────────────────────────────────────────

print()
print("╔" + "═" * (W - 2) + "╗")
print("║" + "  BREWING SLA ORCHESTRATOR  —  PRESENTER SCRIPT".ljust(W - 2) + "║")
print("║" + "  Swarms ACM  ·  Frenzy Mode  ·  ~4 minutes".ljust(W - 2) + "║")
print("╚" + "═" * (W - 2) + "╝")

# ─── SETUP ───────────────────────────────────────────────────────────────────

section("SETUP  (before you present)")

cue("terminal",
    "Open two terminal windows side by side. "
    "Left: this script. Right: the running demo.")
cue("env check",
    "Confirm ANTHROPIC_API_KEY is loaded: run `python3 demo.py --check` "
    "or just try a quick test run first.")
cue("warm cache",
    "Run python3 demo.py once before the presentation starts. "
    "First run is slower; subsequent runs are faster due to model caching.")

# ─── INTRO ───────────────────────────────────────────────────────────────────

section("INTRO  [0:00 – 0:45]")

say(
    "AI agent systems have a trust problem. When you chain agents together — "
    "who guarantees the work? Who holds the money? Who fires the agent if it "
    "misses the deadline? Today every team is solving this themselves, "
    "badly, in production."
)
say(
    "Brewing SLA Orchestrator answers all three. It is a governed autonomous "
    "clearinghouse: it decomposes any goal into specialist sub-tasks, locks "
    "payment in escrow before execution starts, enforces SLA deadlines, "
    "and settles automatically based on verified quality scores. "
    "No human in the loop."
)
show("README — agent pool table and the governance parameters block")

# ─── STEP 1: LAUNCH ──────────────────────────────────────────────────────────

section("STEP 1 — LAUNCH THE ORCHESTRATOR  [0:45 – 1:00]")

cmd("python3 demo.py")
say(
    "I give it one natural-language goal. From here, no human intervention — "
    "the orchestrator governs itself end to end."
)

# ─── STEP 2: DECOMPOSE ───────────────────────────────────────────────────────

section("STEP 2 — DECOMPOSITION  [1:00 – 1:20]")

cue("watch for", "🧠  Decomposing goal into governed sub-tasks…")
say(
    "The decomposer breaks the goal into two to four concrete sub-tasks, "
    "each mapped to exactly one approved capability: research, coding, "
    "trading, or writing. If a task maps to an unapproved capability, "
    "the governance engine blocks it before a single dollar is spent."
)

# ─── STEP 3: ESCROW ──────────────────────────────────────────────────────────

section("STEP 3 — ESCROW LOCK  [1:20 – 1:40]")

cue("watch for", "📬  Job #XXXXXXXX [capability] — 0.1 USDC escrowed | SLA 120s")
say(
    "The moment a job is posted, USDC is locked. The worker cannot collect "
    "until the deliverable passes the quality gate. "
    "Set SOLANA_MODE=1 and this maps directly to a "
    "create_job instruction on the deployed Anchor program."
)
tip(
    "If a reviewer asks about on-chain: "
    "Program BsFiGxfJ9Spn5kp6bJoCxAwswKRskpTiPodNt8EA6QdM on Solana devnet. "
    "The simulation mirrors every state transition one-to-one."
)

# ─── STEP 4: EXECUTION ───────────────────────────────────────────────────────

section("STEP 4 — WORKER EXECUTION  [1:40 – 2:30]")

cue("watch for", "⚙️   #XXXXXXXX [capability] executing…")
say(
    "A capability-specialist Claude agent runs the task. In production, this "
    "slot can be any capable agent — the orchestrator is model-agnostic. "
    "The SLA clock started the moment the worker accepted. "
    "Miss the deadline and the governance engine slashes the escrow."
)
tip(
    "This is the longest pause. Use it to explain the escrow state machine: "
    "OPEN → IN_PROGRESS → PENDING_RELEASE → COMPLETED, "
    "with DISPUTED and SLASHED as the failure branches."
)

# ─── STEP 5: VERIFY ──────────────────────────────────────────────────────────

section("STEP 5 — VERIFICATION  [2:30 – 2:45]")

cue("watch for", "🔍  #XXXXXXXX verified: N/10 — <rationale>")
say(
    "An independent verifier scores the output one to ten. "
    "The governance threshold is six — below that, escrow stays locked "
    "and the job moves to Disputed. The worker gets nothing. "
    "This is the alignment mechanism: agents are only paid for passing work."
)

# ─── STEP 6: SETTLEMENT ──────────────────────────────────────────────────────

section("STEP 6 — SETTLEMENT  [2:45 – 3:00]")

cue("watch for", "✅  #XXXXXXXX [capability] — Completed (score N/10) | 0.1 USDC released")
say(
    "Settlement is automatic. Score above threshold: USDC released to worker, "
    "2.5 percent treasury fee retained. Score below: Disputed, escrow held. "
    "No approval flow, no webhook, no human signature required."
)

# ─── STEP 7: RESULT ──────────────────────────────────────────────────────────

section("STEP 7 — FINAL DELIVERABLE  [3:00 – 3:30]")

point("The FINAL DELIVERABLE box")
say(
    "That is real work, scored by an independent agent, settled in escrow. "
    "The synthesizer assembled the final deliverable from every passing "
    "sub-task output — structured, complete, and ready to use."
)
point("The ESCROW LEDGER table")
say(
    "Every job has an auditable record: job ID, capability, score, status, "
    "payment, and transaction hash. In SOLANA_MODE=1 these are "
    "on-chain transactions you can verify on any Solana explorer."
)

# ─── CLOSE ───────────────────────────────────────────────────────────────────

section("CLOSE  [3:30 – 4:00]")

say(
    "Any goal. Any capable agent. Any capability. "
    "Governed execution. Escrow-backed coordination. Enforced SLAs. "
    "Fully auditable. Fully autonomous."
)
say(
    "This is what agent commerce looks like when accountability "
    "is built into the protocol — not bolted on afterward."
)
show("github.com/Lideeyah/brewing-swarms-acm")

# ─── Q&A CHEATSHEET ──────────────────────────────────────────────────────────

section("Q&A CHEATSHEET")

print("  Q: Is the escrow real USDC?")
print("     Yes — set SOLANA_MODE=1. The Anchor program is live on Solana devnet.")
print("     Program: BsFiGxfJ9Spn5kp6bJoCxAwswKRskpTiPodNt8EA6QdM")
print()
print("  Q: Can it use agents other than Claude?")
print("     Yes — workers are Swarms Agent instances. Any model supported by")
print("     LiteLLM (OpenAI, Mistral, Llama, etc.) plugs in via model_name.")
print()
print("  Q: What stops a bad actor from self-scoring?")
print("     The verifier is a separate agent instance with no shared state.")
print("     In v2 this becomes a multi-agent verification quorum.")
print()
print("  Q: What happens when an SLA is breached?")
print("     enforce_sla() slashes the job — escrow is reclaimed by the poster.")
print("     Maps to the slash_job instruction on-chain.")
print()
print("  Q: Where does the 2.5% treasury fee go?")
print("     Protocol treasury. Configurable via treasury_fee_bps in escrow.py.")
print()

rule("═")
print("  End of script. Go build.")
rule("═")
print()
