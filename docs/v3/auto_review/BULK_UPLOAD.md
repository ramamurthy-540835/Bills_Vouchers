# Bulk uploads
The browser acknowledges each file before awaiting extraction of the batch, instead of waiting for OCR before sending the next file. One rejected file does not prevent remaining dispatches. All job IDs are persisted for refresh recovery with bounded polling backoff. A business mismatch rejects upload before storing under a changed context.

Existing supported formats remain PDF, PNG/JPEG, canonical XLSX and CSV, with 20 files and 15 MB per file under the existing contract. Individual originals and structured row provenance are retained. Future business policy can be overridden OFF for selected files.

ZIP, TIFF, HEIC and arbitrary JSON/XML uploads are not introduced. Logical splitting of multiple invoices inside one PDF is not implemented. Do not present the ZIP acceptance scenario as passed.

Status: implementation candidate; not a complete Auto Review 2.0 release. Local tests are not legal acceptance or live provider acceptance. V2 is excluded.
