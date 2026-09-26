# Red Taxi preview BigQuery seed

On 2026-09-25, the workspace owner explicitly requested that the normal preview
dashboard be populated with the existing synthetic Red Taxi generator output.
This is a specific exception to the earlier file-only demonstration workflow.

- Preview: https://preview---bills-voucher-web-foovqasysa-el.a.run.app/?period=2026-09
- Dataset: `aidirac-503309.finance_analytics`
- Client: `02f66f3a-0981-4db9-8bd3-1870855c4c09` (Red Taxi)
- Period: September 2026
- Run: `synthetic_redtaxi_202609_seed42_v1`
- BigQuery transaction: `f2a0ea8b-2729-41ac-948f-b770fd1173fe`

The empty period received 26 Bronze documents, 26 Silver purchase headers and
lines, six sales, 18 simulated GSTR-2B invoices, 22 Gold ledger entries, 22 match
decisions and one Gold filing summary. Two purchases need review and two represent
failed extraction. Gold values come from the deterministic demonstration generator;
they are not real OCR results, accountant approvals or actual tax entitlements.

Sample input tax is INR 33,204.60, eligible credit INR 20,547.35, output tax
INR 57,360.00 and estimated cash payable INR 36,812.65.

All sample invoice numbers use `RTX-DEMO`; filenames also include `SAMPLE`.
The 26 source attachments are labelled JSON fixtures stored under
`gs://aidirac-503309-bills-voucher-documents/demos/redtaxi/2026-09/synthetic_redtaxi_202609_seed42_v1/`.
They are not invoice images. Existing client identity, GSTIN and user access were
not changed. The normal dashboard reads these records using its existing live
BigQuery path, so its technical `live` mode does not imply genuine transactions.

`scripts/seed_redtaxi_preview.py` defaults to a read-only preflight and requires
`--apply` for writing. It checks the exact client and missing GSTIN, rejects any
nonempty or frozen period, uploads only dedicated sample evidence objects, and
asserts the conditions again within an atomic BigQuery transaction. Running it
again refuses to duplicate the data. Normal application sample-write guards are
unchanged. Local rows, counts, transaction and evidence manifest are retained in
`artifacts/redtaxi-bigquery-seed/`.

Do not treat this seeded period as actual accounts or filing evidence. Keep its
records identifiable when replacing the demonstration with genuine transactions.
The earlier `redtaxi_demo_live_smoke.py` no-mock-live-data assertion predates this
owner-requested load; use `verify_redtaxi_seed.py` for this populated preview.
