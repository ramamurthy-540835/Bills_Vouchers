"""Local CPU benchmarks only. No network requests, customer data or cloud costs."""
import json
import platform
import statistics
import time
from pathlib import Path

from app.gst.comparison import price_breakdown
from app.gst.intake import preview


def measure(function, iterations):
    values = []
    for _ in range(iterations):
        started = time.perf_counter_ns()
        function()
        values.append((time.perf_counter_ns() - started) / 1_000_000)
    ordered = sorted(values)
    return {**{f'p{p}_ms': round(ordered[min(len(ordered)-1, int(len(ordered)*p/100))], 4)
               for p in [50, 90, 95, 99]}, 'iterations': iterations,
            'mean_ms': round(statistics.mean(values), 4)}


def main():
    results = {'scope': 'Local CPU only; not end-to-end or cloud load acceptance.',
               'python': platform.python_version(), 'platform': platform.platform(),
               'declared_rate_arithmetic': measure(lambda: price_breakdown('1180', '18', inclusive=True), 1000)}
    for count in [10, 1000, 10000]:
        rows = [{'source_record_id': str(i), 'event_type': 'invoice', 'invoice_total': '118.00'}
                for i in range(count)]
        results[f'normalize_{count}_rows'] = measure(lambda: preview('vendor', rows), 25)
    path = Path('artifacts/gst_new_v3/local-performance.json')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
