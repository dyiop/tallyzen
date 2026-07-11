"""tally plugin — TallyPrime access for the Accountant agent.

Registers eight read/write tools that the Accountant uses to work the live books.
Each tool is a thin HTTP call to the Tally connector (the seam), which serves
either real TallyPrime or the seeded dataset — the agent only ever sees clean
JSON, never Tally XML.

Follows the Hermes plugin contract: a module-level ``register(ctx)`` that calls
``ctx.register_tool(...)`` once per tool. Enable via ``hermes plugins enable
tally`` (adds it to config) + a gateway restart.

Config:  TALLY_CONNECTOR_URL  (default http://127.0.0.1:8800)
"""

from __future__ import annotations

import json
import logging
import os
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)

BASE_URL = os.environ.get("TALLY_CONNECTOR_URL", "http://127.0.0.1:8800")
TIMEOUT = 8


def _get(path, params=None):
    url = BASE_URL + path
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _post(path, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        BASE_URL + path, data=data,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _ok(obj):
    return json.dumps(obj, ensure_ascii=False)


def _err(message):
    return json.dumps({"error": str(message)}, ensure_ascii=False)


# --- handlers: (args: dict, **kw) -> str -------------------------------------
def handle_sales_by_destination(args, **kw):
    try:
        return _ok(_get("/sales_by_destination"))
    except Exception as e:  # noqa: BLE001 - surface connector errors to the agent
        return _err("Tally connector unreachable: " + str(e))


def handle_sales_by_product(args, **kw):
    try:
        return _ok(_get("/sales_by_product"))
    except Exception as e:  # noqa: BLE001
        return _err("Tally connector unreachable: " + str(e))


def handle_receivables(args, **kw):
    params = {}
    if args.get("overdue_only"):
        params["overdue_only"] = "1"
    if args.get("country"):
        params["country"] = args["country"]
    try:
        return _ok(_get("/receivables", params))
    except Exception as e:  # noqa: BLE001
        return _err("Tally connector unreachable: " + str(e))


def handle_cash_position(args, **kw):
    try:
        return _ok(_get("/cash_position"))
    except Exception as e:  # noqa: BLE001
        return _err("Tally connector unreachable: " + str(e))


def handle_gst_position(args, **kw):
    try:
        return _ok(_get("/gst_position"))
    except Exception as e:  # noqa: BLE001
        return _err("Tally connector unreachable: " + str(e))


def handle_sales_trend(args, **kw):
    try:
        return _ok(_get("/sales_trend"))
    except Exception as e:  # noqa: BLE001
        return _err("Tally connector unreachable: " + str(e))


def handle_find_vendor(args, **kw):
    try:
        return _ok(_get("/vendor", {"name": args.get("name", "")}))
    except Exception as e:  # noqa: BLE001
        return _err("Tally connector unreachable: " + str(e))


def handle_post_voucher(args, **kw):
    payload = {
        "type": args.get("voucher_type", "Purchase"),
        "party": args.get("party", ""),
        "amount": int(args.get("amount", 0)),
        "debit_ledger": args.get("debit_ledger", ""),
        "narration": args.get("narration", ""),
    }
    try:
        return _ok(_post("/voucher", payload))
    except Exception as e:  # noqa: BLE001
        return _err("Tally connector unreachable: " + str(e))


def check_connector():
    try:
        _get("/health")
        return True
    except Exception:  # noqa: BLE001 - unavailable if connector is down
        return False


# --- schemas ------------------------------------------------------------------
_NO_ARGS = {"type": "object", "properties": {}, "required": []}

SALES_BY_DESTINATION_SCHEMA = {
    "name": "tally_sales_by_destination",
    "description": "Six-month export sales by destination country (USA, China, Vietnam, Others): monthly figures, 6-month totals, each country's share, and the ranking. Use for which-markets and market-trend questions.",
    "parameters": _NO_ARGS,
}
SALES_BY_PRODUCT_SCHEMA = {
    "name": "tally_sales_by_product",
    "description": "Six-month revenue by product line (e.g. Vannamei vs Black Tiger prawns), ranked, with the top line named. Use for 'which product line made the most money'.",
    "parameters": _NO_ARGS,
}
RECEIVABLES_SCHEMA = {
    "name": "tally_receivables",
    "description": "Outstanding customer receivables — who owes money, how much, how overdue. Use for collections and cash-risk questions.",
    "parameters": {
        "type": "object",
        "properties": {
            "overdue_only": {"type": "boolean", "description": "Only overdue bills.", "default": False},
            "country": {"type": "string", "description": "Filter by destination country, e.g. 'USA'."},
        },
        "required": [],
    },
}
CASH_POSITION_SCHEMA = {
    "name": "tally_cash_position",
    "description": "Current cash and bank balances and their total. Use for liquidity questions.",
    "parameters": _NO_ARGS,
}
GST_POSITION_SCHEMA = {
    "name": "tally_gst_position",
    "description": "GST position — output tax, input credit, and net payable (negative means a refund is due). This exporter is typically in a refund position.",
    "parameters": _NO_ARGS,
}
SALES_TREND_SCHEMA = {
    "name": "tally_sales_trend",
    "description": "Total monthly sales across all destinations for the last six months. Use for overall revenue-trend questions.",
    "parameters": _NO_ARGS,
}
FIND_VENDOR_SCHEMA = {
    "name": "tally_find_vendor",
    "description": "Look up a vendor/supplier by partial name to check if they exist as a ledger and return their GSTIN. Use during invoice booking.",
    "parameters": {
        "type": "object",
        "properties": {"name": {"type": "string", "description": "Vendor name or fragment."}},
        "required": ["name"],
    },
}
POST_VOUCHER_SCHEMA = {
    "name": "tally_post_voucher",
    "description": "Write a voucher to Tally (e.g. a Purchase voucher when booking a supplier invoice). ALWAYS confirm the details with the owner (via the Advisor) before calling this — it writes to the books.",
    "parameters": {
        "type": "object",
        "properties": {
            "voucher_type": {"type": "string", "description": "e.g. 'Purchase', 'Payment', 'Receipt'."},
            "party": {"type": "string", "description": "Party ledger name (vendor/customer)."},
            "amount": {"type": "integer", "description": "Voucher amount in INR."},
            "debit_ledger": {"type": "string", "description": "The ledger to debit (e.g. 'Packing Material')."},
            "narration": {"type": "string", "description": "Free-text note for the voucher."},
        },
        "required": ["voucher_type", "party", "amount"],
    },
}

_TOOLS = [
    ("tally_sales_by_destination", SALES_BY_DESTINATION_SCHEMA, handle_sales_by_destination, "🌏"),
    ("tally_sales_by_product", SALES_BY_PRODUCT_SCHEMA, handle_sales_by_product, "🦐"),
    ("tally_receivables", RECEIVABLES_SCHEMA, handle_receivables, "📥"),
    ("tally_cash_position", CASH_POSITION_SCHEMA, handle_cash_position, "💰"),
    ("tally_gst_position", GST_POSITION_SCHEMA, handle_gst_position, "🧾"),
    ("tally_sales_trend", SALES_TREND_SCHEMA, handle_sales_trend, "📈"),
    ("tally_find_vendor", FIND_VENDOR_SCHEMA, handle_find_vendor, "🔎"),
    ("tally_post_voucher", POST_VOUCHER_SCHEMA, handle_post_voucher, "✍️"),
]


def register(ctx) -> None:
    """Register the eight Tally tools. Called once by the plugin loader when the
    plugin is enabled in config.yaml."""
    for name, schema, handler, emoji in _TOOLS:
        ctx.register_tool(
            name=name,
            toolset="tally",
            schema=schema,
            handler=handler,
            check_fn=check_connector,
            emoji=emoji,
        )
    logger.info("tally plugin: registered %d tools (toolset=tally)", len(_TOOLS))
