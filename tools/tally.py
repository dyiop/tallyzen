"""
Hermes tool: TallyPrime access for the Accountant agent.

Registers focused, agent-callable tools that read the live books and post
vouchers. Each tool is a thin HTTP call to the Tally connector (the seam), which
serves either real TallyPrime or the seeded dataset — the agent never knows or
cares which. Keeps this file stable whether or not the VM is up.

Drop this file in the Hermes `tools/` directory. Any tools/*.py with a top-level
registry.register() call is auto-discovered — no manual import wiring.

Config:  TALLY_CONNECTOR_URL  (default http://127.0.0.1:8800)
"""

import json
import os
import urllib.parse
import urllib.request

from tools.registry import register

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
        BASE_URL + path, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _as_text(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2)


def tally_sales_by_destination() -> str:
    """Six-month export sales broken down by destination country (USA, China,
    Vietnam, Others): monthly figures, 6-month totals, each country's share, and
    the ranking. Use for questions about which markets the business sells to and
    how they are trending."""
    return _as_text(_get("/sales_by_destination"))


def tally_sales_by_product() -> str:
    """Six-month revenue by product line (e.g. Vannamei vs Black Tiger prawns),
    ranked, with the top line named. Use for 'which product line made the most
    money' style questions."""
    return _as_text(_get("/sales_by_product"))


def tally_receivables(overdue_only: bool = False, country: str = "") -> str:
    """Outstanding customer receivables (who owes money, how much, how overdue).
    Set overdue_only=True for only overdue bills; pass a country to filter (e.g.
    'USA'). Use for collections and cash-risk questions."""
    params = {}
    if overdue_only:
        params["overdue_only"] = "1"
    if country:
        params["country"] = country
    return _as_text(_get("/receivables", params))


def tally_cash_position() -> str:
    """Current cash and bank balances and their total. Use for liquidity /
    'how much cash do I have' questions."""
    return _as_text(_get("/cash_position"))


def tally_gst_position() -> str:
    """Current GST position — output tax, input credit, and net payable (negative
    means a refund is due). This exporter is typically in a refund position."""
    return _as_text(_get("/gst_position"))


def tally_sales_trend() -> str:
    """Total monthly sales across all destinations for the last six months. Use
    for overall revenue-trend questions."""
    return _as_text(_get("/sales_trend"))


def tally_find_vendor(name: str) -> str:
    """Look up a vendor/supplier by (partial) name to check whether they already
    exist as a ledger and return their GSTIN. Use during invoice booking to
    decide if a new ledger is needed."""
    return _as_text(_get("/vendor", {"name": name}))


def tally_post_voucher(voucher_type: str, party: str, amount: int,
                       debit_ledger: str = "", narration: str = "") -> str:
    """Post a voucher to Tally (e.g. a Purchase voucher when booking a supplier
    invoice). ALWAYS confirm the details with the owner before calling this — it
    writes to the books. Returns the created voucher with its number."""
    payload = {
        "type": voucher_type, "party": party, "amount": amount,
        "debit_ledger": debit_ledger, "narration": narration,
    }
    return _as_text(_post("/voucher", payload))


register(name="tally_sales_by_destination", func=tally_sales_by_destination,
         description="Export sales by destination country over six months, with shares and ranking.")
register(name="tally_sales_by_product", func=tally_sales_by_product,
         description="Six-month revenue by product line, ranked, top line named.")
register(name="tally_receivables", func=tally_receivables,
         description="Outstanding receivables; optional overdue_only and country filters.")
register(name="tally_cash_position", func=tally_cash_position,
         description="Current cash and bank balances and total.")
register(name="tally_gst_position", func=tally_gst_position,
         description="GST position; negative net_payable means a refund is due.")
register(name="tally_sales_trend", func=tally_sales_trend,
         description="Total monthly sales for the last six months.")
register(name="tally_find_vendor", func=tally_find_vendor,
         description="Look up a vendor by partial name; returns existence and GSTIN.")
register(name="tally_post_voucher", func=tally_post_voucher,
         description="Write a voucher to Tally. Confirm with the owner first.")
