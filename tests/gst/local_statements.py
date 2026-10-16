"""SQLite statement evidence for the local browser harness only; never cloud data."""
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from fastapi import HTTPException

PATH = Path('artifacts/gst_easy/local-statements.sqlite')


def connect():
    PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(PATH)
    db.execute('CREATE TABLE IF NOT EXISTS imports(client TEXT, period TEXT, digest TEXT, source TEXT, records TEXT, content BLOB, PRIMARY KEY(client,digest))')
    return db


def save(client, period, records, actor, source, content):
    source = {**source, 'actor_id': str(actor), 'imported_at': datetime.now(timezone.utc).isoformat()}
    try:
        with connect() as db:
            db.execute('INSERT INTO imports VALUES(?,?,?,?,?,?)', (client, period, source['sha256'], json.dumps(source), json.dumps(records, default=str), content))
    except sqlite3.IntegrityError:
        raise HTTPException(409, 'This statement was already imported. Refresh before retrying.') from None


def history(client, period):
    with connect() as db:
        return [json.loads(row[0]) for row in db.execute('SELECT source FROM imports WHERE client=? AND period=? ORDER BY rowid DESC', (client, period))]


def records(client, period):
    with connect() as db:
        row = db.execute('SELECT records FROM imports WHERE client=? AND period=? ORDER BY rowid DESC LIMIT 1', (client, period)).fetchone()
        return json.loads(row[0]) if row else []


def original(client, ref):
    with connect() as db:
        for source, content in db.execute('SELECT source,content FROM imports WHERE client=?', (client,)):
            if json.loads(source)['raw_ref'] == ref:
                return content
    return None


def reset():
    with connect() as db:
        db.execute('DELETE FROM imports')
