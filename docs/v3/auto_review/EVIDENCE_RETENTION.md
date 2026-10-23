# Original evidence
Existing authenticated original-file endpoints and private GCS paths remain authoritative. The original preview and full-view actions are unchanged. Auto Review downloads/checks original availability and refuses confirmation when access fails. Server-owned Auto Review metadata is excluded from model output acceptance.

PDF extraction now sends original PDF bytes to the document model rather than replacing the document with embedded text alone. This retains visual evidence for extraction but does not prove that text-layer conflicts, handwriting or duplicate pages are detected accurately. Those require the pending visual evaluation corpus.

No customer evidence is committed. Synthetic screenshots and local diagnostics stay in ignored artifacts. Existing deletion/audit behavior is preserved.

Status: implementation candidate; not a complete Auto Review 2.0 release. Local tests are not legal acceptance or live provider acceptance. V2 is excluded.
