"""
Generate TallyPrime import XML (masters + vouchers) from seed_books.json.

Educational-mode safe: every voucher is dated on the 1st or 2nd of its month
(TallyPrime Educational restricts voucher dates to the 1st/2nd). Monthly export
sales are booked as one sales voucher per country per month, dated the 1st.

Run:  python3 generate_tally_xml.py
Out:  masters.xml, vouchers.xml   (import via Gateway of Tally → Import → Masters,
      then Vouchers; OR POST each to http://<vm-ip>:9000)

NOTE: Tally XML is version-sensitive. If an import complains, fix the offending
tag and re-run — the mock connector remains the guaranteed fallback for the demo.
"""

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SEED = os.path.join(HERE, "..", "seed_books.json")

with open(SEED, "r", encoding="utf-8") as _f:
    BOOKS = json.load(_f)

COMPANY = BOOKS["company"]["name"]


def _esc(text):
    return (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _envelope(inner):
    return (
        '<ENVELOPE>\n'
        '<HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>\n'
        '<BODY><IMPORTDATA>\n'
        '<REQUESTDESC><REPORTNAME>All Masters</REPORTNAME>\n'
        '<STATICVARIABLES><SVCURRENTCOMPANY>' + _esc(COMPANY) + '</SVCURRENTCOMPANY></STATICVARIABLES>\n'
        '</REQUESTDESC>\n'
        '<REQUESTDATA>\n' + inner + '</REQUESTDATA>\n'
        '</IMPORTDATA></BODY>\n'
        '</ENVELOPE>\n'
    )


def _ledger(name, parent, extra=""):
    return (
        '<TALLYMESSAGE>\n'
        '<LEDGER NAME="' + _esc(name) + '" ACTION="Create">\n'
        '<NAME>' + _esc(name) + '</NAME>\n'
        '<PARENT>' + _esc(parent) + '</PARENT>\n'
        + extra +
        '</LEDGER>\n</TALLYMESSAGE>\n'
    )


def _unit(symbol):
    # A stock item's BASEUNITS must reference a Unit of Measure that already
    # exists, so these UNIT masters have to be emitted before any stock item.
    return (
        '<TALLYMESSAGE>\n'
        '<UNIT NAME="' + _esc(symbol) + '" ACTION="Create">\n'
        '<NAME>' + _esc(symbol) + '</NAME>\n'
        '<ISSIMPLEUNIT>Yes</ISSIMPLEUNIT>\n'
        '</UNIT>\n</TALLYMESSAGE>\n'
    )


def _stockitem(name, unit):
    return (
        '<TALLYMESSAGE>\n'
        '<STOCKITEM NAME="' + _esc(name) + '" ACTION="Create">\n'
        '<NAME>' + _esc(name) + '</NAME>\n'
        '<BASEUNITS>' + _esc(unit) + '</BASEUNITS>\n'
        '</STOCKITEM>\n</TALLYMESSAGE>\n'
    )


def build_masters():
    parts = []
    # Sales ledgers, one per destination — gives sales-by-country directly in Tally
    for country in ["USA", "China", "Vietnam", "Others"]:
        parts.append(_ledger("Export Sales - " + country, "Sales Accounts"))
    # Tax + purchase-side ledgers for Flow 1
    parts.append(_ledger("Packing Material", "Purchase Accounts"))
    parts.append(_ledger("Input CGST", "Duties & Taxes"))
    parts.append(_ledger("Input SGST", "Duties & Taxes"))
    # Bank / cash
    for acct in BOOKS["cash_and_bank"]:
        parent = "Bank Accounts" if "Bank" in acct else "Cash-in-Hand"
        parts.append(_ledger(acct, parent))
    # Customers (debtors) with country in the name for legibility
    for r in BOOKS["receivables"]:
        gst_state = '<LEDSTATENAME>' + _esc(r["country"]) + '</LEDSTATENAME>\n'
        parts.append(_ledger(r["customer"], "Sundry Debtors", gst_state))
    # Vendors (creditors)
    for v in BOOKS["vendors"]:
        gstin = '<PARTYGSTIN>' + _esc(v["gstin"]) + '</PARTYGSTIN>\n'
        parts.append(_ledger(v["name"], "Sundry Creditors", gstin))
    # Units of measure — must be created before any stock item references them
    seen_units = []
    for it in BOOKS["stock_items"]:
        unit = it.get("unit", "kg")
        if unit not in seen_units:
            seen_units.append(unit)
            parts.append(_unit(unit))
    # Stock items
    for it in BOOKS["stock_items"]:
        parts.append(_stockitem(it["item"], it.get("unit", "kg")))
    return _envelope("".join(parts))


def _sales_voucher(date, party, sales_ledger, amount):
    return (
        '<TALLYMESSAGE>\n'
        '<VOUCHER VCHTYPE="Sales" ACTION="Create">\n'
        '<DATE>' + date + '</DATE>\n'
        '<VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>\n'
        '<PARTYLEDGERNAME>' + _esc(party) + '</PARTYLEDGERNAME>\n'
        '<ALLLEDGERENTRIES.LIST>\n'
        '<LEDGERNAME>' + _esc(party) + '</LEDGERNAME>\n'
        '<ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>\n'
        '<AMOUNT>-' + str(amount) + '</AMOUNT>\n'
        '</ALLLEDGERENTRIES.LIST>\n'
        '<ALLLEDGERENTRIES.LIST>\n'
        '<LEDGERNAME>' + _esc(sales_ledger) + '</LEDGERNAME>\n'
        '<ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>\n'
        '<AMOUNT>' + str(amount) + '</AMOUNT>\n'
        '</ALLLEDGERENTRIES.LIST>\n'
        '</VOUCHER>\n</TALLYMESSAGE>\n'
    )


def _country_party(country):
    # Pick a representative debtor per country for the monthly aggregate voucher.
    for r in BOOKS["receivables"]:
        if r["country"] == country:
            return r["customer"]
    return "Export Sales - " + country  # fallback


def build_vouchers():
    parts = []
    s = BOOKS["sales_by_destination"]
    for i, month in enumerate(s["months"]):
        day = "01"
        date = month.replace("-", "") + day  # YYYYMMDD, all on the 1st
        for country in ["USA", "China", "Vietnam", "Others"]:
            amount = s[country][i]
            if amount <= 0:
                continue
            party = _country_party(country)
            parts.append(_sales_voucher(date, party, "Export Sales - " + country, amount))
    return _envelope("".join(parts))


def main():
    with open(os.path.join(HERE, "masters.xml"), "w", encoding="utf-8") as f:
        f.write(build_masters())
    with open(os.path.join(HERE, "vouchers.xml"), "w", encoding="utf-8") as f:
        f.write(build_vouchers())
    print("Wrote masters.xml and vouchers.xml for " + COMPANY)
    print("Import order: Masters first, then Vouchers (Gateway of Tally → Import).")


if __name__ == "__main__":
    main()
