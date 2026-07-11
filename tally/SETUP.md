# Tally setup — get a live server going for the demo

You run these steps inside the Windows VM (Parallels). Budget ~15 min. The **mock
connector is the guaranteed fallback** — if real Tally fights you, the demo still works.

## 1. Install TallyPrime (Windows VM)
1. Download TallyPrime from tallysolutions.com and install.
2. Launch → on the license screen choose **Educational Version** (free, no key).
   - Educational mode restricts voucher dates to the **1st/2nd of any month** — our seed
     already dates everything on the 1st, so this is a non-issue.
3. **Create Company**: name `Meenakshi Marine Exports`, Country India, State Tamil Nadu,
   enable GST. (Financial year 2026-27.)

## 2. Enable the HTTP-XML gateway (this is the port the agent hits)
1. In TallyPrime: `F1 (Help) → Settings → Connectivity → Client/Server configuration`.
2. Set **TallyPrime acts as: Server**. **Port: 9000**. Save.
3. Windows firewall: allow inbound TCP **9000**; add `tally.exe` and `tallygw.exe` to
   antivirus/firewall exceptions (this fixes most "can't connect" issues).
4. Keep at least one company loaded — the gateway only answers when a company is open.

## 3. Load the seed data (one-time import)
From the repo on the VM (or copy `tally/import/*.xml` over):
1. `Gateway of Tally → Import → Masters` → select `masters.xml` → import.
2. `Gateway of Tally → Import → Vouchers` → select `vouchers.xml` → import.
   - Regenerate anytime with `python3 tally/import/generate_tally_xml.py`.
   - Tally XML is version-sensitive; if a tag is rejected, fix and re-import. Not blocking —
     the mock covers the demo regardless.

## 4. Point the connector at real Tally
On the machine running the connector (Mac or VM):
```
# Find the VM's IP first (in Windows: ipconfig)
export TALLY_HTTP=http://<vm-ip>:9000
python3 tally/tally_connector.py
```
Then implement the `_tally_*` helpers in `tally_connector.py` to POST TDL/XML to
`TALLY_HTTP` (see `tally/import/generate_tally_xml.py` for the envelope shapes). Until then,
leave `TALLY_HTTP` unset and the connector serves the seed — identical JSON to the agent.

## 5. Verify (run this before you demo)
```
bash tally/verify.sh
```
It starts the connector and checks every endpoint returns the expected shape. Green = the
Accountant agent will get real answers.

## The agent side (no VM needed)
- `TALLY_CONNECTOR_URL` (default `http://127.0.0.1:8800`) tells `tools/tally.py` where the
  connector is. Set it if the connector runs on a different host than Hermes.
- The agent only ever sees the connector's clean JSON — it never touches Tally XML.
