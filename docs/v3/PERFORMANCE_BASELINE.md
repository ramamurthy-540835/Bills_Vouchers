# Local performance baseline

Executed `scripts/benchmark_gst_new_v3.py` on Windows 11 / Python 3.14.7 with
synthetic inputs. Raw results: `artifacts/gst_new_v3/local-performance.json`.

| Operation | Iterations | p50 ms | p95 ms | p99 ms |
|---|---:|---:|---:|---:|
| Declared-rate Decimal arithmetic | 1000 | 0.0031 | 0.0033 | 0.0056 |
| Normalize 10 rows | 25 | 0.0852 | 0.0925 | 0.1939 |
| Normalize 1,000 rows | 25 | 8.8416 | 9.2154 | 9.5940 |
| Normalize 10,000 rows | 25 | 91.1637 | 94.3628 | 100.2264 |

These exclude file transfer, authentication, BigQuery, GCS, queue dispatch and AI.
No prior-version comparison or end-to-end improvement percentage is asserted.
Remote API percentiles, queue lag, concurrent users and cost remain unmeasured.
