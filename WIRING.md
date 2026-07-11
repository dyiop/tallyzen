# Wiring tools into Hermes — shared understanding

For the two of us to stay in sync: this is **where tool definitions live** and **how they
reach the agent**. Key thing to internalize up front:

> There are **two** ways a tool enters Hermes, and we're each using a different one.
> **Accountant tools = a Python plugin.  Analyst (Linkup) = an MCP server.**
> Both end up as tools the agent can call — they just load differently.

---

## The layered picture

```
   Agent (a Hermes profile: Advisor / Accountant / Analyst)
        │  calls a tool by name
        ▼
   Tool registry  ── every callable tool lives here, no matter how it got in
        ▲                         ▲
        │ (mechanism 1)           │ (mechanism 2)
   PLUGIN                     MCP SERVER
   register(ctx) →            declared in config.yaml
   ctx.register_tool(...)     mcp_servers: { linkup: ... }
        │                         │
   our Tally tools            Linkup web research
        │
   HTTP JSON → Tally connector (:8800 mock / real Tally :9000) → the books
```

---

## Mechanism 1 — the Accountant tools (our plugin)

**Where the definitions live (source of truth, versioned):**
`hermes-plugin/tally/`
- `plugin.yaml` — metadata + `provides_tools:` (the 8 tool names).
- `__init__.py` — the actual definitions: for each tool a **JSON schema** + a **handler**,
  wired in a module-level `register(ctx)`.

**The 8 tools:** `tally_sales_by_destination`, `tally_sales_by_product`, `tally_receivables`,
`tally_cash_position`, `tally_gst_position`, `tally_sales_trend`, `tally_find_vendor`,
`tally_post_voucher`.

**The plugin contract (what Hermes actually calls) — one entrypoint:**
```python
def register(ctx) -> None:
    for name, schema, handler, emoji in _TOOLS:
        ctx.register_tool(
            name=name,          # tool name the model calls
            toolset="tally",    # the group it belongs to (gated per platform, see below)
            schema=schema,      # JSON schema: {name, description, parameters:{type:object,...}}
            handler=handler,    # handler(args: dict, **kw) -> str   (returns JSON string)
            check_fn=check_connector,  # availability gate (is the connector up?)
            emoji=emoji,
        )
```
A handler is just `handler(args, **kw) -> str`: pull params out of `args`, call the connector
over HTTP, return `json.dumps(...)`. No Tally XML anywhere near the agent — the connector
isolates that.

**How it loads into the running Hermes (already done for `tally`):**
1. **Install** — copy `hermes-plugin/tally/` → `~/.hermes/plugins/tally/`
   *(Hermes discovers plugins from `~/.hermes/plugins/`.)*
2. **Enable** — `hermes plugins enable tally`
   → writes `plugins.enabled: [tally]` into `~/.hermes/config.yaml`.
   *(We declined the "override built-in tools" privilege — we only ADD tools.)*
3. **Expose the toolset** — a toolset must be listed per platform or the agent won't see it.
   Added `tally` under `known_plugin_toolsets.cli` and `.telegram` in config.
4. **Restart the gateway** — `hermes gateway run --replace` (loads plugins at startup).

**Current state:** installed ✅ · enabled ✅ · toolset exposed on cli+telegram ✅ ·
**needs a gateway restart to go live** ⏳.

---

## Mechanism 2 — the Analyst tools (Linkup, MCP)

Linkup is **already wired** — it's an MCP server in `~/.hermes/config.yaml`:
```yaml
mcp_servers:
  linkup:
    url: https://mcp.linkup.so/mcp
    headers:
      Authorization: Bearer ${MCP_LINKUP_API_KEY}
    enabled: true          # ← already true
```
Hermes connects to the MCP server and its tools appear in the same registry the agent calls.
**Nothing to build for the tool layer** — the Analyst's job is the *profile/prompt* that uses
Linkup well (bounded queries, credible sources), not plumbing. Confirm `MCP_LINKUP_API_KEY`
is set in `~/.hermes/.env`.

**Plugin vs MCP — when to use which:**
- **Plugin** (our Tally): the integration is our own code / talks to something local (the
  connector, the VM). Python, in-process, `register(ctx)`.
- **MCP** (Linkup): a ready-made external tool server. Just declare it in config; no code.

---

## The Advisor + how delegation ACTUALLY works (read this — it's not obvious)

The Advisor is the **gateway-facing agent** — the one the owner messages on Telegram. It
orchestrates the other two and does all the presentation. Two facts from the Hermes source
that shape everything:

**1. Delegated children INHERIT the Advisor's toolsets — the model can't pick them.**
There is no "Accountant profile" that delegation targets by name. The Advisor calls the
`delegate_task` tool with a `goal`, `context`, and a `role` label ("Accountant"/"Analyst").
The spawned child **inherits whatever toolsets the Advisor has**, and the role+goal steer how
it behaves. Consequence: **the Advisor (the Telegram agent) must itself hold every toolset any
specialist needs** →  `delegation` + `tally` + `charts` + the **Linkup** MCP toolset.
Delegation is **serial** — delegate to the Accountant, get the result, then the Analyst.

**2. Presentation is the Advisor's OWN job, not delegated.** It gathers raw numbers via the
specialists, then builds the answer itself:
- **Charts** — the `charts` plugin (`chart_bar`, `chart_line`) renders a PNG and returns a
  **`MEDIA:<path>`** string.
- **Sending images** — the platform delivers any `MEDIA:<path>` the agent puts in its reply
  as a native image (same convention TTS/screenshots use). One `MEDIA:` line per message =
  one image message. The Advisor sends each chart as its own message + a 1–2 line explainer.

Identity prompts live in `profiles/{advisor,analyst,accountant}.md`.

### Wiring checklist for the Advisor (Telegram agent)
- `delegation` toolset on telegram — ✅ already on.
- `tally` toolset — ✅ enabled + exposed.
- `charts` toolset — ✅ enabled + exposed (this piece).
- **`linkup` MCP toolset exposed on telegram — ⚠️ NOT yet.** Linkup is enabled as an MCP
  *server*, but its toolset must be reachable by the Telegram agent so a delegated Analyst
  child inherits it. **Teammate's dependency** — until then the Analyst half of a decision
  can't research. (`inherit_mcp_toolsets` defaults true, so once the parent has it, children
  get it.)
- Gateway restart to load `charts` + pick up the profiles.

---

## Shared memory — the "case file" (agents coordinate through it)
The `context` plugin (`hermes-plugin/context/`) gives all three agents a shared store of
**typed records** keyed by client org: `invoice` (Advisor writes after booking), `signal`
(Analyst writes after research), `note`. `get_company_context` returns the profile + key
facts + recent invoices + recent signals as one brief. This is how agents talk to each
other through memory: the Analyst stores a signal, the Advisor pulls context next turn and
sees it. Verified end-to-end.

**No separate connector** — unlike Tally (which hides XML + a VM), Convex is a clean Python
call, so the store logic lives *inside the plugin*: local JSON file by default
(`~/.hermes/cache/tallyzen-memory/store.json`), real Convex when `CONVEX_URL` is set. We use
**typed tools** (`remember_invoice`, not raw `convex_mutation`) so the schema lives in code,
not in the model's head — fewer ways to fail live. Convex flip = `memory/convex/README.md`
(one browser login you run yourself; earns the Convex power-up).

## Who owns what
| Piece | Mechanism | Owner | Status |
|---|---|---|---|
| Accountant tools (Tally) | Plugin (`hermes-plugin/tally/`) | us | built, enabled, needs gateway restart |
| Tally connector + seed | HTTP seam (`tally/`) | us | working (mock; real VM importing) |
| Charts (Advisor's visuals) | Plugin (`hermes-plugin/charts/`) | us | built, enabled, needs gateway restart |
| Shared memory (case file) | Plugin (`hermes-plugin/context/`) | us | built, enabled, local now; Convex flip ready |
| Advisor profile + delegation | `delegate_task` + `profiles/advisor.md` | us | prompt done; needs restart + live test |
| Analyst tools (Linkup) | MCP server (config) | teammate | server enabled; **toolset not exposed on telegram**; needs prompt |
| Advisor↔Analyst decision flow | inherited `linkup` toolset | together | blocked on Linkup toolset exposure |

## Verify the Accountant end (anytime)
```bash
python3 tally/tally_connector.py     # start the seam (:8800)
bash    tally/verify.sh              # checks all 8 endpoints → all green
```
Then over Telegram after a gateway restart: *"What were my sales by destination country?"*
→ Accountant calls `tally_sales_by_destination` → "USA 62%, down 30% over two months…".
