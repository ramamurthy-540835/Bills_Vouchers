"""Discovered V4 coordinates shared by operator-only scripts, not application code."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from audit_gst_v4 import ART, cloud  # noqa: E402

_baseline=json.loads((ART/'protected-before.json').read_text())
PROJECT=_baseline['project']
REGION=_baseline['region']
PREFIX='gst_easy_v4_'
