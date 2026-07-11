# demo/ — assets for the live demo

## `coastal-packaging-invoice.png`
The sample supplier invoice to upload to the Telegram bot for **Flow 1** (invoice → book
voucher in Tally). Its figures match `tally/seed_books.json → flow1_sample_invoice`:

| Field | Value |
|---|---|
| Supplier | Coastal Packaging Pvt Ltd (GSTIN `33AAECC5678L1Z3`, Tamil Nadu) |
| Buyer | Meenakshi Marine Exports (GSTIN `33AABCM1234K1Z9`) |
| Invoice | CP/INV-2231 · 02-Jul-2026 |
| Item | Thermocol export boxes (5 kg) · HSN 3923 · 3,000 × ₹50 |
| Tax | Taxable ₹1,50,000 + CGST 9% ₹13,500 + SGST 9% ₹13,500 |
| **Total** | **₹1,77,000** |

Intra-state (both parties in Tamil Nadu) ⇒ CGST + SGST, not IGST.

**Expected booking** (Purchase voucher): `Coastal Packaging Pvt Ltd` **Cr ₹1,77,000** /
`Packing Material` **Dr ₹1,77,000**. Both ledgers already exist in Tally.

`coastal-packaging-invoice.html` is the source; regenerate the PNG with headless Chrome
(`--screenshot`) if you edit it.

> Fictional parties and GSTINs — sample data for demonstrating the pipeline, not a real
> financial document.
