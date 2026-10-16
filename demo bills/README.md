# Nature Labs synthetic upload pack

28 distinct invoices (12 manufacturing, 8 trading, 8 services), each in PDF, PNG and JPEG. Upload ONE representation per invoice. All are fictional and marked NOT VALID FOR TAX FILING. No real bank details are used. GSTIN-like identifiers satisfy checksum but are not verified taxpayer identities. Do not use outside the isolated V2 demo.

The environment is provisioned with profiles ONLY. Upload files yourself, review extracted values and confirm valid invoices before expecting financial dashboard/report figures. Select October 2026. Expected totals are in EXPECTED_RESULTS.xlsx; monetary calculations use Decimal. ITC remains pending until evidence-based review. Test rates (12%, 18%) and HSN/SAC assignments are assumptions, not current-law advice.

GSTR-2B fixtures contain supported B2B matches, amount/tax-head differences and statement-only records. Other purchases are books-only after import. Duplicate statements in edge_cases must be rejected; credit-note GSTR sections are unsupported, not simulated. Imported statements never approve ITC. Edge-case outcomes are in TEST_MANIFEST.json. Credit notes use positive face amounts and negative signed financial contributions.

Use python scripts/generate_gst_easy_v2_demo.py to regenerate with Pillow, ReportLab and openpyxl. Generator has no cloud or application API calls. Logos are fictional programmatic monograms.
