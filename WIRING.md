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

## The agents themselves — profiles + delegation (next step, NOT done yet)

Each of our three "agents" is a **Hermes profile** = `model + toolset access + identity
prompt`. Identity prompts drafted in `profiles/{advisor,analyst,accountant}.md`.

- **Accountant** profile → toolset `tally` (+ its prompt). Reads/writes the books.
- **Analyst** profile → the Linkup MCP tools (+ its prompt). Researches the world.
- **Advisor** profile → the **`delegation`** toolset (already enabled on telegram ✅). It's
  the orchestrator: the owner messages the Advisor, which delegates to the other two and
  synthesizes. Delegation is **serial** in the documented API — delegate to Accountant, get
  the result, then Analyst; don't assume parallel.

Turning the three markdown prompts into live Hermes profiles + wiring delegation is the piece
we do **together next**, after the Accountant is confirmed live over Telegram.

---

## Who owns what
| Piece | Mechanism | Owner | Status |
|---|---|---|---|
| Accountant tools (Tally) | Plugin (`hermes-plugin/tally/`) | us | built, enabled, needs gateway restart |
| Tally connector + seed | HTTP seam (`tally/`) | us | working (mock; real VM importing) |
| Analyst tools (Linkup) | MCP server (config) | teammate | wired; needs prompt/profile |
| Advisor orchestration | `delegation` toolset + profiles | together | next |

## Verify the Accountant end (anytime)
```bash
python3 tally/tally_connector.py     # start the seam (:8800)
bash    tally/verify.sh              # checks all 8 endpoints → all green
```
Then over Telegram after a gateway restart: *"What were my sales by destination country?"*
→ Accountant calls `tally_sales_by_destination` → "USA 62%, down 30% over two months…".
