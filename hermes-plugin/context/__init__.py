"""context plugin — shared business memory ("the case file") for the agents.

The three agents coordinate through a shared store: the Analyst writes market
signals, the Advisor writes the basic fields of every invoice it books, and any
agent can pull the company context (profile + recent invoices + recent signals)
as a brief.

Storage is embedded here (no separate connector) with two modes:
  - LOCAL (default): a JSON file at ~/.hermes/cache/tallyzen-memory/store.json.
    Works offline, zero deps, demo-safe.
  - CONVEX (set CONVEX_URL=https://<deployment>.convex.cloud): the SAME reads and
    writes go to a real Convex deployment via the Convex Python client
    (`pip install convex`). Deploy the functions in memory/convex/ first.

Company profiles are seeded from company_seed.json bundled beside this file.

Config:  CONVEX_URL           (unset => local mode)
         TALLYZEN_ORG         (default 'meenakshi' — the active client)
"""

from __future__ import annotations

import json
import logging
import os
import time

logger = logging.getLogger(__name__)

CONVEX_URL = os.environ.get("CONVEX_URL", "")
ORG = os.environ.get("TALLYZEN_ORG", "meenakshi")
HERE = os.path.dirname(os.path.abspath(__file__))
SEED_PATH = os.path.join(HERE, "company_seed.json")
DATA_DIR = os.path.expanduser("~/.hermes/cache/tallyzen-memory")
STORE_PATH = os.path.join(DATA_DIR, "store.json")

with open(SEED_PATH, "r", encoding="utf-8") as _f:
    COMPANIES = json.load(_f)["companies"]

_convex_client = None


def _now():
    return int(time.time())


def _get_convex():
    global _convex_client
    if _convex_client is None:
        from convex import ConvexClient  # lazy: only imported in Convex mode
        _convex_client = ConvexClient(CONVEX_URL)
    return _convex_client


def _load_store():
    if not os.path.exists(STORE_PATH):
        return {"records": []}
    with open(STORE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_store(store):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(store, f, indent=2, ensure_ascii=False)


def _remember(kind, data):
    ts = _now()
    if CONVEX_URL:
        _get_convex().mutation("memory:remember", dict(org=ORG, kind=kind, data=data, ts=ts))
        return {"stored": True, "kind": kind, "data": data, "backend": "convex"}
    store = _load_store()
    record = {"id": len(store["records"]) + 1, "org": ORG, "kind": kind, "data": data, "ts": ts}
    store["records"].append(record)
    _save_store(store)
    return {"stored": True, "record": record, "backend": "local"}


def _recall(kind=None, limit=20):
    if CONVEX_URL:
        rows = _get_convex().query("memory:recall", dict(org=ORG, kind=kind, limit=limit))
        return rows or []
    store = _load_store()
    rows = [r for r in store["records"] if r["org"] == ORG and (kind is None or r["kind"] == kind)]
    return sorted(rows, key=lambda r: -r["ts"])[:limit]


def _company_context():
    company = COMPANIES.get(ORG)
    if company is None:
        return {"error": "unknown org", "org": ORG, "known": list(COMPANIES.keys())}
    return {
        "company": company,
        "recent_invoices": [r["data"] for r in _recall(kind="invoice", limit=10)],
        "recent_signals": [r["data"] for r in _recall(kind="signal", limit=10)],
        "recent_notes": [r["data"] for r in _recall(kind="note", limit=10)],
        "backend": "convex" if CONVEX_URL else "local",
    }


def _ok(obj):
    return json.dumps(obj, ensure_ascii=False)


def _err(msg):
    return json.dumps({"error": str(msg)}, ensure_ascii=False)


# --- handlers -----------------------------------------------------------------
def handle_get_company_context(args, **kw):
    try:
        return _ok(_company_context())
    except Exception as e:  # noqa: BLE001
        return _err("Memory unavailable: " + str(e))


def handle_remember_invoice(args, **kw):
    data = {"invoice_no": args.get("invoice_no", ""), "value": args.get("value", 0),
            "company": args.get("company", "")}
    if args.get("direction"):
        data["direction"] = args["direction"]
    try:
        return _ok(_remember("invoice", data))
    except Exception as e:  # noqa: BLE001
        return _err("Memory unavailable: " + str(e))


def handle_remember_signal(args, **kw):
    data = {"topic": args.get("topic", ""), "finding": args.get("finding", ""),
            "source": args.get("source", "")}
    try:
        return _ok(_remember("signal", data))
    except Exception as e:  # noqa: BLE001
        return _err("Memory unavailable: " + str(e))


def handle_remember_note(args, **kw):
    data = {"agent": args.get("agent", ""), "text": args.get("text", "")}
    try:
        return _ok(_remember("note", data))
    except Exception as e:  # noqa: BLE001
        return _err("Memory unavailable: " + str(e))


def handle_recall_memory(args, **kw):
    try:
        return _ok({"records": _recall(kind=args.get("kind"), limit=int(args.get("limit", 20)))})
    except Exception as e:  # noqa: BLE001
        return _err("Memory unavailable: " + str(e))


# --- schemas ------------------------------------------------------------------
GET_CONTEXT_SCHEMA = {
    "name": "get_company_context",
    "description": "Pull the shared 'case file' for the current client: company profile + key facts + recent invoices + recent market signals the team has stored. Call this at the START of handling a request so you have the business context and know what the other agents have already found.",
    "parameters": {"type": "object", "properties": {}, "required": []},
}
REMEMBER_INVOICE_SCHEMA = {
    "name": "remember_invoice",
    "description": "Store the basic fields of an invoice into shared memory after it has been booked. Keep it minimal — invoice number, value, and the company/vendor — so the whole team can see what was booked.",
    "parameters": {
        "type": "object",
        "properties": {
            "invoice_no": {"type": "string", "description": "Invoice number."},
            "value": {"type": "number", "description": "Invoice total (INR)."},
            "company": {"type": "string", "description": "Vendor or customer name."},
            "direction": {"type": "string", "description": "Optional: 'purchase' or 'sales'."},
        },
        "required": ["invoice_no", "value", "company"],
    },
}
REMEMBER_SIGNAL_SCHEMA = {
    "name": "remember_signal",
    "description": "Store a market/regulatory signal into shared memory (Analyst uses this): a short finding plus its source, so the Advisor and future turns can reuse it without re-researching.",
    "parameters": {
        "type": "object",
        "properties": {
            "topic": {"type": "string", "description": "Short topic, e.g. 'China market access'."},
            "finding": {"type": "string", "description": "The finding in one or two lines."},
            "source": {"type": "string", "description": "Where it came from (site/body), one phrase."},
        },
        "required": ["topic", "finding"],
    },
}
REMEMBER_NOTE_SCHEMA = {
    "name": "remember_note",
    "description": "Store a free-text note into shared memory for the team (a decision made, something to follow up).",
    "parameters": {
        "type": "object",
        "properties": {
            "agent": {"type": "string", "description": "Who is noting (Advisor/Accountant/Analyst)."},
            "text": {"type": "string", "description": "The note."},
        },
        "required": ["text"],
    },
}
RECALL_SCHEMA = {
    "name": "recall_memory",
    "description": "List records previously stored in shared memory. Optionally filter by kind ('invoice', 'signal', 'note'). Use to check what the team already knows before acting.",
    "parameters": {
        "type": "object",
        "properties": {
            "kind": {"type": "string", "description": "Optional filter: 'invoice', 'signal', or 'note'."},
            "limit": {"type": "integer", "description": "Max records (default 20)."},
        },
        "required": [],
    },
}

_TOOLS = [
    ("get_company_context", GET_CONTEXT_SCHEMA, handle_get_company_context, "🗂️"),
    ("remember_invoice", REMEMBER_INVOICE_SCHEMA, handle_remember_invoice, "🧾"),
    ("remember_signal", REMEMBER_SIGNAL_SCHEMA, handle_remember_signal, "📡"),
    ("remember_note", REMEMBER_NOTE_SCHEMA, handle_remember_note, "📝"),
    ("recall_memory", RECALL_SCHEMA, handle_recall_memory, "🔁"),
]


def register(ctx) -> None:
    """Register the shared-memory tools. Called once when the plugin is enabled."""
    for name, schema, handler, emoji in _TOOLS:
        ctx.register_tool(name=name, toolset="context", schema=schema, handler=handler, emoji=emoji)
    logger.info("context plugin: registered %d tools (toolset=context, backend=%s)",
                len(_TOOLS), "convex" if CONVEX_URL else "local")
