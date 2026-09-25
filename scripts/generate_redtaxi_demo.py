"""Create the Red Taxi demo handoff pack without writing live customer data."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.services.gst.filing_workspace import csv_bytes
from app.services.gst.redtaxi_mock import generate_redtaxi_mock_data, png_prompts


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--period',default='2026-09')
    parser.add_argument('--seed',type=int,default=42)
    parser.add_argument('--output',type=Path,default=Path('artifacts/redtaxi-demo-2026-09'))
    args=parser.parse_args()
    bundle=generate_redtaxi_mock_data(args.period,args.seed)
    args.output.mkdir(parents=True,exist_ok=True)
    files={'mock-data.json':json.dumps(bundle,indent=2,ensure_ascii=False).encode('utf-8'),
           'PNG-PROMPTS.md':png_prompts(bundle).encode('utf-8')}
    for name,rows in [('sales',bundle['outward']),('gstr2b',bundle['gstr2b']),('itc-decisions',bundle['ledger'])]:
        files[name+'.csv']=csv_bytes(rows,list(rows[0]) if rows else [])
    files['README-AUDITORS.md']=(Path(__file__).resolve().parents[1]/'docs/README-REDTAXI-AUDITORS.md').read_bytes()
    files['manifest.json']=json.dumps({'sample':True,'period':args.period,'seed':args.seed,
        'sha256':{name:hashlib.sha256(body).hexdigest() for name,body in files.items()}},indent=2).encode()
    for name,body in files.items():
        (args.output/name).write_bytes(body)
    print(f"Created {len(bundle['documents'])} sample purchases, {len(bundle['outward'])} sales and {len(bundle['gstr2b'])} GSTR-2B rows in {args.output}.")
    print('The frontend Red Taxi scenario uses this same generator. No live financial records or PNG images were created.')


if __name__=='__main__':
    main()
