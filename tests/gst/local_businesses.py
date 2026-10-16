"""SQLite adapter for synthetic browser tests only; never a cloud repository.

Exercises production creation and profile validation with durable local records.
The BigQuery transaction itself still requires separate integration acceptance.
"""
import json
import sqlite3
from pathlib import Path
from google.api_core.exceptions import BadRequest

PATH = Path('artifacts/gst_easy/business-fixtures.sqlite')


def connect():
    PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(PATH)
    db.execute('CREATE TABLE IF NOT EXISTS businesses (id TEXT PRIMARY KEY, owner TEXT, original TEXT, profile TEXT)')
    db.execute('CREATE TABLE IF NOT EXISTS markers (id TEXT PRIMARY KEY)')
    return db


def reset():
    with connect() as db:
        db.execute('DELETE FROM businesses')
        db.execute('DELETE FROM markers')


def profiles(owner):
    with connect() as db:
        return {cid: json.loads(profile) for cid, profile in db.execute('SELECT id, profile FROM businesses WHERE owner=?', (owner,))}


def storage(cid):
    with connect() as db:
        db.execute('INSERT OR IGNORE INTO markers VALUES (?)', (cid,))


class Repository:
    def __init__(self):
        from types import SimpleNamespace
        self.settings = SimpleNamespace(gcp_project_id='synthetic-local')

    def table(self, name):
        return 'synthetic.' + name

    def query(self, sql, params):
        values = {p.name: p.value for p in params}
        with connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if 'customer_created' in sql:
                v = values
                original = {key: v[key] for key in ('name', 'gstin', 'website')}
                existing = db.execute('SELECT owner, original FROM businesses WHERE id=?', (v['cid'],)).fetchone()
                if existing:
                    if existing[0] != v['uid']:
                        raise BadRequest('Customer ownership changed')
                    if json.loads(existing[1]) != original:
                        raise BadRequest('BUSINESS_REQUEST_CHANGED')
                    return []
                if v['gstin'] and db.execute("SELECT 1 FROM businesses WHERE json_extract(profile, '$.gstin')=?", (v['gstin'],)).fetchone():
                    raise BadRequest('BUSINESS_GSTIN_EXISTS')
                profile = dict(profile_id=v['cid'], legal_name=v['name'], trade_name=v['name'],
                               gstin=v['gstin'], pan=v['pan'], state_code=v['state'], website_url=v['website'],
                               contact_email=v['email'], contact_person=v['person'], filing_frequency='monthly',
                               gstin_verified=False, onboarding_completed=False)
                db.execute('INSERT INTO businesses VALUES(?,?,?,?)', (v['cid'], v['uid'], json.dumps(original), json.dumps(profile)))
            elif 'profile_update' in sql:
                v = values
                row = db.execute('SELECT profile FROM businesses WHERE id=? AND owner=?', (v['client_id'], v['actor'])).fetchone()
                if not row or json.loads(row[0])['profile_id'] != v['previous']:
                    raise BadRequest('Profile changed; reload')
                profile = json.loads(v['after_profile'])
                profile.update(profile_id=v['new_id'], onboarding_completed=v['onboarding'])
                db.execute('UPDATE businesses SET profile=? WHERE id=?', (json.dumps(profile), v['client_id']))
            else:
                raise AssertionError('Unsupported synthetic repository operation')
        return []
