# V4 future-provider isolation

The only customer-facing filing path is Method A. The current runtime has no installed/approved GSP, live filing, live GSTR-2B, official GSTIN lookup, e-invoice, e-way bill, or notification adapter.

`app/services/gst/future_providers.py` defines fail-closed capability gates. Each configuration flag defaults to false, and a flag alone cannot activate the feature because the adapter registry is intentionally empty. No customer API routes are mounted for these future providers. The Business Profile provides only a manual official GST Portal lookup link and GSTIN format status; it does not display a provider integration setup or automatic lookup action.

Before any future provider is enabled, require an approved provider contract, security/privacy review, customer consent, Secret Manager configuration, explicit per-feature implementation, independent tests, and release approval. Do not reuse this Method A package/download or evidence workflow as an implicit live provider call.
