# Bill review and original preview

Replaced the oversized native iframe with a client-side PDF.js first-page renderer and contained image preview. PDF.js and its worker/fonts/CMaps/WASM are served from the same frontend, pinned to the installed version; no CDN or public document URL. See https://mozilla.github.io/pdf.js/examples/ for the rendering pattern.

Both preview and View Original Bill use the unchanged authenticated original endpoint, in a separate tab. Full PDFs retain all pages. The preview reports the page count. CSV/XLSX use a file fallback; failed or protected originals retain the open-original action without blocking review. Images preserve aspect ratio with object-fit: contain. Document data stays in component memory; image object URLs and PDF tasks are cleaned up on unmount.

The review layout is 60/40 on wide screens, stacked below 1100px, with identity/status then preview then form on mobile. Form/totals spacing and rejection textarea/actions are scoped to the drawer. No financial calculations, invoice records, API authorization or workflow transitions changed. Docker now copies generated public PDF assets into the standalone runtime.

Changed implementation: frontend/app/bills/original-invoice-preview.tsx, bills-panel.tsx, frontend/app/gst-easy.css, frontend/scripts/prepare-pdfjs.mjs, frontend/package.json and lockfile, frontend/Dockerfile, .gitignore. Tests: tests/frontend/invoice-preview.spec.ts.

Executed: TypeScript and Next production build passed; Ruff passed; 212 GST backend tests passed (three existing warnings). Seven new preview tests passed, including real PDF rendering, two-page PDF, PNG/JPEG, spreadsheet and failure fallbacks, keyboard original navigation, responsive overflow and saving edits. Existing five upload regressions passed. First new test run failed because of test-fixture/hydration timing and native new-tab/download handling; test harness corrected, no backend protections weakened. Desktop/mobile synthetic screenshots visually inspected in artifacts/gst_easy_v2/review-{1440,900,390}.png.

Dependency audit: no PDF.js advisory reported. Existing Next 16.3.4 has production advisories, including next/og ImageResponse; this focused UI change does not remediate those existing framework findings. Full framework security upgrade requires separate regression review. No automated force-upgrade applied.

Deployment targets only gst-easy-v2-web after successful immutable build and staged static-asset checks. API/email configuration stays unchanged. Previous services are compared against the preserved baseline. No cloud invoices are seeded or changed to test this UI. Rollback: route only V2 web to its prior revision recorded in artifacts/gst_easy_v2/review-web-before.json; keep API and existing production/preview services untouched.

Final full frontend suite: 74 passed (2.5 minutes). Backend GST suite: 212 passed. TypeScript, production build, Ruff and diff checks passed. Screenshot and browser fixtures use local synthetic data only.

Deployed to https://gst-easy-v2-web-foovqasysa-el.a.run.app using revision gst-easy-v2-web-00003-til. Cloud Build f12d1b8e-41a7-462e-93b2-f785d8ae1bd6 succeeded from commit b82adffed6805dda0e1704d1060ae47602efee43. Image digest: sha256:fae2e96e4e6ea3e6ad8612783f80bfede5b5a0682014d78df5e75d2056acae4f. Staged login/PDF worker returned 200 before V2 routing changed. V2 API and all previous service/IAM baselines remained unchanged. Rollback target: gst-easy-v2-web-00002-9sc (V2 frontend only).

Live read-only acceptance passed: demo sign-in, deployed PDF worker, preview of an existing generated invoice, identical preview/full-original destinations, and authenticated original HTTP 200. Financial mutations: zero. Evidence: artifacts/gst_easy_v2/review-live-results.json and review-deployment.json. No live invoices were seeded for testing.
