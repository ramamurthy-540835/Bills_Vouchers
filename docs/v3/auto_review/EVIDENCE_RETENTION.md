# Original evidence
Existing authenticated original-file endpoints and private GCS paths remain authoritative. The original preview and full-view actions are unchanged. Auto Review downloads/checks original availability and refuses confirmation when access fails. Server-owned Auto Review metadata is excluded from model output acceptance.

PDF extraction sends original PDF bytes to the document model rather than replacing the document with embedded text alone. The extraction record now retains page count and two conservative text-visible flags: repeated page text and distinct invoice numbers within one PDF. Both prevent automatic confirmation. A repeated page can be checked by an authorized reviewer; a PDF with multiple visible invoice numbers requires separate uploads before confirmation. The generated synthetic PDF tests exercise these boundaries. Image-only PDFs, conflicting hidden text, handwriting and actual model reading accuracy still require an independently labeled visual evaluation corpus.

No customer evidence is committed. Synthetic screenshots and local diagnostics stay in ignored artifacts. Existing deletion/audit behavior is preserved.

Status: implementation candidate; not a complete Auto Review 2.0 release. Local tests are not legal acceptance or live provider acceptance. V2 is excluded.
