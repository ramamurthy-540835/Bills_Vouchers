"""Reuse reviewed V3 release checks with a new tag, retaining Auto Review 1.0."""
import sys
from pathlib import Path

import release_v3_auto_review_candidate as release

release.ART=Path(__file__).resolve().parents[1]/'artifacts/intelligence-v3'
release.TAG='intelligence'

if __name__=='__main__':
    {'build':release.build,'deploy':release.deploy,'verify':release.verify_preserved}[sys.argv[1]]()
