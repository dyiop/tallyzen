"""
Tally connector — the seam between the Hermes agents and the books.

Serves the seeded Meenakshi Marine dataset as clean JSON so `tools/tally.py`
stays simple (JSON in/out) whether or not real TallyPrime is up. All the messy,
version-specific Tally XML parsing is isolated HERE, in one place.

Two modes, one interface:
  - MOCK (default): reads AND writes answered from seed_books.json. Zero deps.
  - HYBRID (set TALLY_HTTP=http://<vm-ip>:9000): reads still come from the seed
    (rich, full-6-month figures), but voucher WRITES POST a real <VOUCHER> Import
    envelope to the live Tally gateway (_tally_post_voucher) so booked invoices
    appear in Tally. The agent-facing routes below do NOT change.

Run:  python3 tally_connector.py          # serves http://127.0.0.1:8800
Try:  curl http://127.0.0.1:8800/sales_by_destination
"""

import json
import os
import re
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

HOST = "127.0.0.1"
PORT = 8800
TALLY_HTTP = os.environ.get("TALLY_HTTP", "")  # empty => mock mode
SEED_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seed_books.json")

with open(SEED_PATH, "r", encoding="utf-8") as _f:
    BOOKS = json.load(_f)


def _sum(values):
    return sum(values)


def get_sales_by_destination():
    s = BOOKS["sales_by_destination"]
    countries = ["USA", "China", "Vietnam", "Others"]
    totals = {c: _sum(s[c]) for c in countries}
    grand = _sum(totals.values())
    ranked = sorted(totals.items(), key=lambda kv: -kv[1])
    share = {c: round(100.0 * totals[c] / grand, 1) for c in countries}
    return {
        "months": s["months"],
        "monthly": {c: s[c] for c in countries},
        "totals_6m": totals,
        "share_pct": share,
        "grand_total_6m": grand,
        "ranked": [{"country": c, "total": t, "share_pct": share[c]} for c, t in ranked],
        "note": s["note"],
    }


def get_sales_by_product():
    lines = BOOKS["product_lines"]
    ranked = sorted(lines, key=lambda l: -l["revenue_6m"])
    return {"product_lines": ranked, "top_line": ranked[0]["line"] if ranked else None}


def get_receivables(overdue_only=False, country=None):
    rows = BOOKS["receivables"]
    if overdue_only:
        rows = [r for r in rows if r["days_overdue"] > 0]
    if country:
        rows = [r for r in rows if r["country"].lower() == country.lower()]
    rows = sorted(rows, key=lambda r: (-r["days_overdue"], -r["amount"]))
    return {"count": len(rows), "total": _sum([r["amount"] for r in rows]), "customers": rows}


def get_cash_position():
    cb = BOOKS["cash_and_bank"]
    return {"accounts": cb, "total": _sum(cb.values())}


def get_gst_position():
    return BOOKS["gst_position"]


def get_sales_trend():
    s = BOOKS["sales_by_destination"]
    countries = ["USA", "China", "Vietnam", "Others"]
    monthly_total = [sum(s[c][i] for c in countries) for i in range(len(s["months"]))]
    return {"months": s["months"], "monthly_total": monthly_total}


def find_vendor(name):
    q = (name or "").lower()
    for v in BOOKS["vendors"]:
        if q and q in v["name"].lower():
            return {"found": True, "vendor": v}
    return {"found": False, "query": name}


def post_voucher(payload):
    vtype = payload.get("type", "Purchase")
    party = payload.get("party", "")
    amount = int(payload.get("amount", 0))
    debit = payload.get("debit_ledger", "")
    narration = payload.get("narration", "")
    if TALLY_HTTP:
        return _tally_post_voucher(payload)  # real Tally path (implement below)
    voucher = {
        "type": vtype, "date": BOOKS["as_of_date"], "party": party,
        "debit_ledger": debit, "amount": amount, "narration": narration,
        "voucher_no": "V-" + str(100 + len(BOOKS.get("_posted", []))),
        "status": "posted (mock)",
    }
    BOOKS.setdefault("_posted", []).append(voucher)
    return {"created": True, "voucher": voucher}


# --- Real TallyPrime hooks (POST vouchers to the live gateway on TALLY_HTTP) -----
def _esc(text):
    return (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _educational_safe_date():
    # TallyPrime Educational restricts voucher dates to the 1st/2nd of any month, so
    # book on the 2nd of the as-of month (also matches the seed's Flow-1 invoice date).
    as_of = BOOKS.get("as_of_date", "2026-07-02")  # "YYYY-MM-DD"
    return as_of[0:4] + as_of[5:7] + "02"


def _voucher_xml(vtype, party, debit_ledger, amount, narration, date):
    # Two-line voucher: debit the expense/asset ledger, credit the party. Tally sign
    # convention (see generate_tally_xml.py): debit = ISDEEMEDPOSITIVE Yes + negative
    # AMOUNT; credit = ISDEEMEDPOSITIVE No + positive AMOUNT.
    company = BOOKS["company"]["name"]
    return (
        '<ENVELOPE>\n'
        '<HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>\n'
        '<BODY><IMPORTDATA>\n'
        '<REQUESTDESC><REPORTNAME>All Masters</REPORTNAME>\n'
        '<STATICVARIABLES><SVCURRENTCOMPANY>' + _esc(company) + '</SVCURRENTCOMPANY></STATICVARIABLES>\n'
        '</REQUESTDESC>\n'
        '<REQUESTDATA>\n<TALLYMESSAGE>\n'
        '<VOUCHER VCHTYPE="' + _esc(vtype) + '" ACTION="Create">\n'
        '<DATE>' + date + '</DATE>\n'
        '<VOUCHERTYPENAME>' + _esc(vtype) + '</VOUCHERTYPENAME>\n'
        '<PARTYLEDGERNAME>' + _esc(party) + '</PARTYLEDGERNAME>\n'
        '<NARRATION>' + _esc(narration) + '</NARRATION>\n'
        '<ALLLEDGERENTRIES.LIST>\n'
        '<LEDGERNAME>' + _esc(debit_ledger) + '</LEDGERNAME>\n'
        '<ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>\n'
        '<AMOUNT>-' + str(amount) + '</AMOUNT>\n'
        '</ALLLEDGERENTRIES.LIST>\n'
        '<ALLLEDGERENTRIES.LIST>\n'
        '<LEDGERNAME>' + _esc(party) + '</LEDGERNAME>\n'
        '<ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>\n'
        '<AMOUNT>' + str(amount) + '</AMOUNT>\n'
        '</ALLLEDGERENTRIES.LIST>\n'
        '</VOUCHER>\n</TALLYMESSAGE>\n'
        '</REQUESTDATA>\n</IMPORTDATA></BODY>\n'
        '</ENVELOPE>\n'
    )


def _tag_int(text, tag):
    m = re.search("<" + tag + ">(-?\\d+)</" + tag + ">", text)
    return int(m.group(1)) if m else 0


def _tag_text(text, tag):
    m = re.search("<" + tag + ">(.*?)</" + tag + ">", text, re.DOTALL)
    return m.group(1).strip() if m else ""


def _tally_import(xml):
    req = urllib.request.Request(
        TALLY_HTTP, data=xml.encode("utf-8"),
        headers={"Content-Type": "text/xml"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8", "replace")


def _tally_post_voucher(payload):
    # Build a <VOUCHER> Import Data envelope and POST it to the live Tally gateway.
    vtype = payload.get("type", "Purchase")
    party = payload.get("party", "")
    amount = int(payload.get("amount", 0))
    # Debit ledger must exist in Tally; "Packing Material" is the seeded purchase ledger.
    debit = payload.get("debit_ledger", "") or "Packing Material"
    narration = payload.get("narration", "")
    date = _educational_safe_date()
    xml = _voucher_xml(vtype, party, debit, amount, narration, date)
    try:
        resp = _tally_import(xml)
    except Exception as e:  # noqa: BLE001 - gateway down / VM unreachable
        return {"created": False, "error": "Tally gateway unreachable: " + str(e)}
    created = _tag_int(resp, "CREATED")
    errors = _tag_int(resp, "ERRORS")
    exceptions = _tag_int(resp, "EXCEPTIONS")
    lineerror = _tag_text(resp, "LINEERROR")
    ok = created > 0 and errors == 0 and exceptions == 0
    voucher = {
        "type": vtype, "date": date, "party": party,
        "debit_ledger": debit, "amount": amount, "narration": narration,
        "status": "posted (live Tally)" if ok else "rejected by Tally",
    }
    result = {"created": ok, "voucher": voucher,
              "tally": {"created": created, "errors": errors, "exceptions": exceptions}}
    if lineerror:
        result["tally"]["lineerror"] = lineerror
    return result


def _route_get(path, query):
    if path in ("/", "/health"):
        return {"ok": True, "company": BOOKS["company"]["name"], "mode": "real" if TALLY_HTTP else "mock"}
    if path == "/sales_by_destination":
        return get_sales_by_destination()
    if path == "/sales_by_product":
        return get_sales_by_product()
    if path == "/receivables":
        overdue = query.get("overdue_only", ["0"])[0] in ("1", "true")
        country = query.get("country", [None])[0]
        return get_receivables(overdue_only=overdue, country=country)
    if path == "/cash_position":
        return get_cash_position()
    if path == "/gst_position":
        return get_gst_position()
    if path == "/sales_trend":
        return get_sales_trend()
    if path == "/vendor":
        return find_vendor(query.get("name", [""])[0])
    return {"error": "unknown route", "path": path}


class Handler(BaseHTTPRequestHandler):
    def _send(self, obj, code=200):
        body = json.dumps(obj, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        self._send(_route_get(parsed.path, parse_qs(parsed.query)))

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        parsed = urlparse(self.path)
        if parsed.path == "/voucher":
            self._send(post_voucher(json.loads(raw or b"{}")))
        else:
            self._send({"error": "unknown route", "path": parsed.path}, code=404)

    def log_message(self, *args):
        return


def main():
    mode = "REAL → " + TALLY_HTTP if TALLY_HTTP else "MOCK (seed)"
    print("Tally connector [" + mode + "] for " + BOOKS["company"]["name"])
    print("Serving http://" + HOST + ":" + str(PORT) + "  — try /sales_by_destination")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
