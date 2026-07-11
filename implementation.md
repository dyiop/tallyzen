# Tallyzen — Implementation on Hermes
*How the three-agent financial firm (see [`tallyzen-plan.md`](./tallyzen-plan.md)) is actually
built on the Hermes agent runtime. Hermes Buildathon · Track 03.*

---

## The one thing to internalize
**Hermes is not an SDK you build agents *in* (like the OpenAI Agents SDK). It is a complete
agent *runtime* you build *on top of*.**

You do **not** write an agent loop. Hermes already *is* the loop — `AIAgent.run_conversation()`
in `run_agent.py` handles prompt construction, tool dispatch, retries, provider fallback,
memory, and persistence. You bring three things:

1. **Tools** — your integrations (Tally, Linkup, TTS) registered as Python functions.
2. **Profiles** — each "agent" *is* a Hermes **profile**: a bundle of
   `(model + tools + skills + identity prompt)`. You don't write an `Advisor` class; you
   configure an Advisor *profile*.
3. **Delegation** — the Advisor spawns the Analyst and Accountant via the built-in
   `delegate_tool.py`.

**Mental-model flip:** in a typical framework an "agent" is an *object you instantiate and
wire in code*. In Hermes an "agent" is a *profile* the runtime loads, and "multi-agent" is
one profile **delegating** to another through a tool call. Our three agents aren't three
programs — they're three profiles + a Tally tool + a Linkup tool, all inside one runtime.
Far less code than a from-scratch build — which is the point on an 8-hour clock.

---

## Architecture with Hermes in the loop

```
   Business owner  ──(WhatsApp / Telegram)──►  Hermes GATEWAY  (hermes gateway)
                                                     │  adapter → AIAgent.run_conversation()
                                                     ▼
                                    ┌────────────────────────────────┐
                                    │  ADVISOR profile  (orchestrator)│
                                    │  model + identity prompt        │
                                    │  tools: delegate_tool, TTS      │
                                    └────────────────────────────────┘
                                       │ delegate_tool           │ delegate_tool
                                       ▼                          ▼
                        ┌───────────────────────┐   ┌───────────────────────────┐
                        │  ANALYST profile       │   │  ACCOUNTANT profile        │
                        │  tool: linkup (web)    │   │  tool: tally (your :9000)  │
                        └───────────────────────┘   └───────────────────────────┘
                                    │                            │
                              Live web research            TallyPrime XML
                                                                 │
                        shared skills  ~/.hermes/skills/   ·   memory: SQLite + FTS5
```

### Mapping our concepts onto Hermes primitives
| Our concept | Hermes primitive | How we build it |
|---|---|---|
| **Advisor** (face + orchestrator) | Main **profile** bound to the gateway | Identity prompt + `delegate_tool` + a TTS tool (ElevenLabs). The profile the WhatsApp/Telegram session hits. |
| **Analyst** (outward) | A **profile** with a web tool | Give it the **Linkup** tool (or Nous Portal bundled web search). Advisor delegates research tasks to it. |
| **Accountant** (inward) | A **profile** with a **Tally tool** | Wrap `tally_connector.py` calls as a registered tool: `tools/tally.py` → `register(name="tally_query", ...)`. Auto-discovered, no import wiring. |
| **Invoice→Tally chain** (Flow 1) | Tools + a **skill** | Vision extraction + validation + a `tally.post_voucher` tool. The recurring booking logic becomes a **skill** Hermes writes and reuses. |
| **WhatsApp / Telegram surface** | The **gateway** | `hermes gateway` — 20 platform adapters ship in the box. This is why the messaging surface is nearly free. |
| **"Case file" memory** | Native **SQLite + FTS5** memory | See decision #2 below — Hermes may replace the Convex plan here. |

---

## How the parts work (concrete, with file/function names)

**Single agent** — the loop lives in `AIAgent` (`run_agent.py`), entry
`run_conversation()`. `hermes_cli/runtime_provider.py` maps `(provider, model)` → API mode +
credentials across 18+ providers. Tool calls dispatch through `model_tools.py`.

**Custom tools** — create `tools/my_tool.py`:
```python
from tools.registry import register

def tally_query(question: str) -> str:
    """Query the live TallyPrime books (receivables, sales, cash, etc.)."""
    ...  # calls our connector at :9000
    return result

register(name="tally_query", func=tally_query, description="Read the live Tally books")
```
Any `tools/*.py` with a top-level `registry.register()` call is **auto-discovered** — no
manual import list. This is where `tally_connector.py` becomes a first-class Hermes tool.

**Multi-agent** — `delegate_tool.py` lets one agent spawn child agents with tailored
context. **Sub-agents are defined as Hermes profiles** (each = model + tools + skills +
identity prompt). The Advisor delegates to the Accountant and Analyst profiles.

**Memory** — `agent/memory_manager.py` over `hermes_state.py` (SQLite + FTS5), per-profile
isolated, with parent/child session lineage. Memory providers are single-select per profile.

**Skills** — the closed learning loop: Hermes writes reusable skill docs to
`~/.hermes/skills/` (shared across agents on the machine, `agentskills.io`-compatible).
Managed via the `skill_manage` tool.

**Gateway** — `hermes gateway` runs a long-lived process; `gateway/platforms/` holds ~20
adapters (Telegram, WhatsApp, Discord, Slack, Signal…). Flow: `Adapter.on_message()` →
`MessageEvent` → `GatewayRunner._handle_message()` → auth → session → fresh
`AIAgent.run_conversation()` → reply via adapter.

**Programmatic entry** — `from run_agent import AIAgent` for a Python-library entry point
alongside CLI/gateway/cron/ACP. **MCP** is supported — any tool can be exposed via an MCP
server and Hermes connects to it (an alternative to a native `tools/*.py` wrapper for Tally).

---

## Two decisions this forces — settle them before building

**1. Delegation is serial, not parallel (per the official docs).** Nous docs describe
`delegate_tool` for hand-off but state parallel spawning/orchestration "isn't a documented
subsystem" and "requires custom code." (A third-party site markets first-class parallel
orchestration — do **not** bet an 8-hour build on the undocumented claim.) For Flow 2, have
the Advisor delegate to the Accountant, **then** the Analyst, sequentially, and synthesize.
Slightly slower; the judge sees the same coordination; bulletproof.

**2. Hermes gives memory for free — does Convex still earn its slot?** Hermes ships
persistent memory (SQLite + FTS5). Options: (a) **drop Convex**, use native memory, spend
the slot elsewhere; (b) keep Convex as the *shared business "case file"* distinct from agent
conversation memory; (c) write Convex as a Hermes **memory-provider plugin**. For the
hackathon, lean (a) unless you specifically want the Convex power-up points — don't run two
memory systems for a demo.

**Showcase the skills loop.** When the Accountant first books a voucher or runs the export
breakdown, let Hermes write a reusable skill (e.g. `book_purchase_voucher`) — shared across
the firm, so the whole team gets better mid-session. One demo line — "watch it write itself
a skill the first time, then reuse it" — directly shows the platform's signature capability,
the closed learning loop the buildathon is named for.

---

## What this means for the build

- **We write far less than a from-scratch build.** No agent loop, no orchestration engine,
  no message router, no WhatsApp integration. We write: **one Tally tool**
  (`tools/tally.py` wrapping the existing connector), wire **Linkup**, define **three
  profiles** with identity prompts, add **ElevenLabs TTS** as a tool.
- **`tally_connector.py` is not wasted** — it becomes the guts of the registered Tally tool.
  Same code, now callable by the Accountant profile.
- **Eligibility = "Hermes as base harness"** (the stronger path): the product runs on Hermes
  and the judge interacts with it live over Telegram/WhatsApp. Keep coding-partner receipts
  too (free extra qualification).
- **First thing on repo access:** clone `NousResearch/hermes-agent`, run `hermes setup`, get
  **one** profile talking to Telegram with **one** trivial custom tool. That spine
  (gateway → agent → tool → reply) is the whole ballgame; everything else is adding profiles
  and tools to a working skeleton.

### Build order
1. Spine: gateway → Advisor profile → one trivial tool → reply on Telegram.
2. `tools/tally.py` wrapping `tally_connector.py`; Accountant profile reads the books.
3. Advisor delegates to Accountant (serial). Land a Flow-2 read end to end.
4. Analyst profile + Linkup; Advisor delegates research; synthesize both → reply.
5. Flow 1: vision extraction + `tally.post_voucher` + validation (Linkup GSTIN).
6. ElevenLabs TTS on the Advisor's final reply. Harden the two happy paths.
7. Let Hermes write/reuse a skill on the booking path (showcase the loop). Save receipts.

---

## References
- Hermes docs — https://hermes-agent.nousresearch.com/docs/
- Architecture guide — https://hermes-agent.nousresearch.com/docs/developer-guide/architecture
- GitHub — https://github.com/nousresearch/hermes-agent
- Multi-agent orchestration — https://hermes-agent.ai/features/multi-agent
- awesome-hermes-agent (tools/skills) — https://github.com/0xNyk/awesome-hermes-agent
