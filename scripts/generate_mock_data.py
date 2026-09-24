"""Generate repeatable frontend examples without credentials or cloud writes.

python scripts/generate_mock_data.py --scenario all --period 2026-09 --output artifacts/mock-data.json
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.gst.mock_data import SCENARIOS, generate_mock_data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenario', choices=['all', *SCENARIOS], default='all')
    parser.add_argument('--period', default='2026-09')
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--output', type=Path, default=Path('artifacts/mock-data.json'))
    args = parser.parse_args()
    names = list(SCENARIOS) if args.scenario == 'all' else [args.scenario]
    payload = {'sample': True, 'scenarios': {name: generate_mock_data(name, args.period, args.seed) for name in names}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'Created {len(names)} synthetic scenarios in {args.output}. No cloud records changed.')


if __name__ == '__main__':
    main()
