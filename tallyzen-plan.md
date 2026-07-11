# Tallyzen — An AI Financial Services Firm
*Hermes Buildathon · Track 03 (AI as Agency) · canonical plan.
Mirrors the live doc: https://www.html-docs.com/site/tallyzen-the-ai-accounts-agency-50f6
Supersedes the earlier `GAMEPLAN.md`, `agency-shape.md`, `demand-and-agents.md`.*

**A financial services firm, run by agents.** Three agents that work like a real finance
team — a **Financial Advisor** who talks to the owner, a **Financial Analyst** who
researches the outside world, and an **Accountant** who reads the books in TallyPrime.
They coordinate to do the work *and* to answer the hard questions. Built on Hermes.

---

## What we're judged on (the effective rubric)
A mentor confirmed the three things to prioritize. Every design choice serves one of these:
1. **An end-to-end workflow** — a complete job, from the owner's request to a real
   outcome. Not a menu of features.
2. **Agents coordinating** — multiple agents visibly handing off and combining their work
   toward one outcome.
3. **Tools in action** — the partner tools doing real work *inside* the flow, not bolted on.

---

## The firm — three agents, one team
The Advisor is the face *and* the orchestrator. It never answers alone — it spawns the
Analyst (the outside world) and the Accountant (the books), then synthesizes.

Colour code (functional, used in the diagram + flow steps):
**amber = Advisor / synthesis · teal = Analyst / outward · green = Accountant / inward.**

| Agent | Role | Does | Tool(s) |
|---|---|---|---|
| **Financial Advisor** | the face + orchestrator | Talks to the owner, frames the question, delegates, fuses inputs into one recommendation, delivers it. | Hermes · ElevenLabs · Wispr Flow |
| **Financial Analyst** | the outward eye | Researches demand, prices, rates, regulatory conditions, competitors — and what they mean for the decision. | Linkup (live web) |
| **Accountant** | the inward eye | Speaks with TallyPrime. Pulls current reality (sales, cash, receivables, payables) and posts entries. | TallyPrime XML :9000 |

Escalation: anything statutory (filing, audit, uncertainty) → **hand to the human CA.**
Honest, trustworthy, and keeps the accountant an ally rather than a target.

```
                     Business owner · WhatsApp / voice
                                   │
                     ┌─────────────────────────────┐        ┌───────────────────┐
                     │   FINANCIAL ADVISOR  (amber) │◄──────►│ Shared memory      │
                     │   face · plans · synthesizes │        │ Convex (case file) │
                     └─────────────────────────────┘        └───────────────────┘
                          │                        │
              ┌───────────┘                        └───────────┐
              ▼                                                 ▼
   ┌──────────────────────┐                        ┌──────────────────────┐
   │ FINANCIAL ANALYST     │                        │ ACCOUNTANT            │
   │ (teal) market/reg     │                        │ (green) the books     │
   │ tool: Linkup          │                        │ tool: TallyPrime :9000│
   └──────────────────────┘                        └──────────────────────┘
              ▼                                                 ▼
     Live web · rates, markets                     Tally books · vouchers, sales
                                                             │
                                             escalate ▼ your CA (statutory)
```

---

## Flow 1 · the opener — upload an invoice → it lands in Tally
The #1 ask across a year of waitlist (40% of signups). Proves the plumbing — and it's a
**coordinated chain, not one agent.**

1. **Advisor** — receives the invoice photo/PDF on WhatsApp/Telegram, opens a job,
   delegates. *(Wispr Flow · Hermes)*
2. **Extraction agent · vision** — image → structured fields: vendor, GSTIN, date, line
   items, taxable value, CGST/SGST/IGST, total. *(GPT-5.5 vision)*
3. **Validation & Enrichment agent** — checks the tax math and whether the vendor exists
   as a ledger; unknown vendor / missing GSTIN → verifies live via **Linkup**; flags
   anything unresolved.
4. **Booking agent** — maps to the correct ledgers, builds the voucher, posts to Tally on
   confirm, returns the voucher number. *(TallyPrime :9000 · Convex audit trail)*
5. **Advisor** → owner: *"Booked INV-2231 from Bajaj Steel — ₹1,50,000 (₹1,27,119 +
   ₹22,881 GST) as Purchase voucher V-104. Vendor GSTIN verified via Linkup."*

**End-to-end:** raw document → verified, posted voucher → confirmation.

---

## Flow 2 · the showpiece — a seafood trader decides where to sell next
The Advisor can't answer this alone. It needs the books (Accountant) and the market
(Analyst) at once — which is exactly what makes the coordination real.

**Persona:** Meenakshi Marine Exports · Thoothukudi, Tamil Nadu · prawn exporter.
**Trigger (owner, by voice):** *"With the US–Iran war, my US orders are drying up. Look at
my last six months of prawn sales and tell me — should I shift to China, Vietnam and
Southeast Asia?"*

1. **Advisor** — frames the decision, states the plan, spawns two requests in parallel.
   *(Wispr Flow · Hermes)*
2. **Accountant → Tally** — 6 months of prawn sales by destination + customer:
   *"₹4.2 Cr total — 62% to the US, and US is down 30% over the last two months. Top US
   buyer Gulf Coast Seafood owes ₹38 L, 55 days overdue. China 16%, Vietnam 12%."*
   *(TallyPrime :9000)*
3. **Analyst → Linkup** — the outside world: *"China vannamei demand is strong; Vietnam is
   a re-processing hub for Indian raw material; the US carries anti-dumping duties on
   Indian shrimp and freight/insurance is spiking. Selling to China needs GACC + MPEDA
   registration (~weeks)."* *(Linkup)*
4. **Advisor synthesizes → voice** — fuses internal + external into one recommendation,
   spoken back. *(ElevenLabs · Convex)*

**Outcome:** *"Your books already confirm the US is softening and ₹38 L is stuck there. The
market backs the pivot: prioritize China — but start the GACC/MPEDA registration now, it's
the long pole. Keep Vietnam as a re-processing channel, hold a small US allocation for
paying buyers only, and collect that ₹38 L before extending more US credit. Loop your CHA
in on the China paperwork."*

**Grounded, not hallucinated:** Indian shrimp leaning on the US — and the live debate about
diversifying to China and SE Asia — is a *real industry story*. Point Linkup at real
destination-market and regulatory data; let the "US–Iran war" be the narrative shock that
starts the question. The Analyst returns facts a judge can verify.

---

## Priority 3 · tools in action — every tool has a real job
| Tool | Job |
|---|---|
| **Hermes** | Base harness — all three agents run on it and accrete reusable skills. |
| **TallyPrime :9000** | Accountant posts vouchers (F1) and reads sales & receivables (F2). |
| **Linkup** | GSTIN/vendor lookup (F1) · market & regulatory research (F2). |
| **GPT-5.5 vision** | Extraction agent reads the invoice image into structured fields (F1). |
| **ElevenLabs** | Advisor delivers the recommendation as speech (F2). |
| **Wispr Flow** | Owner asks by voice — dictation into the Advisor. |
| **Convex** | Shared "case file" memory across agents and turns. |
| **Cloudflare** | Hosts the webhook / agent surface on a live URL. |

*Dodo Payments doesn't fit an advisory flow cleanly — include it only as an "activate your
plan" checkout, or leave it out. A natural tool story beats a forced one.*

---

## Grounding & build discipline
**Real demand behind it:** 40% of a year of waitlist asked for invoice → Tally (Flow 1);
80% of signups are ₹50 Lakh ARR and up (established SMBs, India-first); 67% said yes to a
founder call (20 high-intent businesses to validate with).

**Build discipline (8-hour clock):**
- Bound the Analyst's research to 2–3 concrete Linkup queries. Bounded = reliable.
- Rehearse **one** happy path per flow; harden it.
- Make every handoff **visible** — each agent posts its own line so the judge *sees* the
  coordination (that's what priority #2 needs).
- Flow 2 (advisory) is the demo showpiece; note it reaches beyond the bookkeeping the
  waitlist asked for.

**Outstanding:** `seed_books.json` is still the generic hardware business — Flow 2 needs
Meenakshi Marine's 6-month prawn sales by destination country + the overdue US buyer before
the Accountant can return those numbers.
