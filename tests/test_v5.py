import ast
import copy
import re
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware

from app.config import get_settings
from app.db import get_db
from app.routes import current_user
from app.services.gst import medallion, pipeline, workbench
from app.services.gst.medallion import Medallion, clear_cache, live_only
from app.services.gst.rules import amount, common_reversal, deadline, rule, set_off


class Row(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)


class MemoryRepo:
    dataset = "test.finance"

    def __init__(self):
        self.tables = {}
        self.queries = []

    def table(self, name):
        return self.dataset + "." + name

    def query(self, sql, params=None):
        self.queries.append((sql, params))
        p = {x.name: x.value for x in params or []}
        if sql.startswith("DELETE"):
            table = re.search(r"test.finance.(\w+)", sql)[1]
            self.tables[table] = [r for r in self.tables.get(table, []) if not (r.get("client_id") == p.get("client_id") and r.get("doc_id") == p.get("doc_id"))]
            return []
        if sql.startswith("BEGIN"):
            state = next((r for r in self.tables.get("gst_filing_status", []) if r["client_id"] == p["client_id"] and r["period"] == p["period"] and r["is_current"]), None)
            assert (state["state"] if state else "draft") == p["expected"]
            if state:
                state["is_current"] = False
            self.tables.setdefault("gst_filing_status", []).append(Row(client_id=p["client_id"], period=p["period"], state=p["target"], is_current=True, effective_from="2026-09-24"))
            self.tables.setdefault("gst_filing_audit", []).append(Row(client_id=p["client_id"], period=p["period"], to_state=p["target"]))
            return []
        table = re.search(r"FROM `test.finance.(\w+)`", sql)[1]
        rows = copy.deepcopy(self.tables.get(table, []))
        for col, key in (("client_id", "client_id"), ("period", "period"), ("doc_id", "doc_id"), ("run_id", "run_id"), ("content_hash", "hash"), ("supplier_gstin", "supplier"), ("invoice_no", "number")):
            if re.search(rf"\b{col}=@{key}\b", sql):
                rows = [r for r in rows if r.get(col) == p[key]]
        if "doc_id!=@doc_id" in sql:
            rows = [r for r in rows if r.get("doc_id") != p["doc_id"]]
        if "is_current=TRUE" in sql:
            rows = [r for r in rows if r.get("is_current")]
        if "validation_status='validated'" in sql:
            rows = [r for r in rows if r.get("validation_status") == "validated"]
        return [Row(r) for r in rows]


class Objects:
    def __init__(self, *_):
        self.objects = {}

    def upload(self, path, data, mime):
        self.objects[path] = data
        return "gs://test/" + path


@pytest.fixture
def repo(monkeypatch):
    monkeypatch.setenv("DEMO_FALLBACK", "false")
    get_settings.cache_clear()
    medallion._cache.clear()
    repo = MemoryRepo()
    def write(self, table, row, keys):
        live_only(row)
        assert row["client_id"] == self.client_id
        rows = self.repo.tables.setdefault(table, [])
        existing = next((r for r in rows if all(r.get(k) == row.get(k) for k in keys)), None)
        if existing:
            existing.update(copy.deepcopy(row))
        else:
            rows.append(Row(copy.deepcopy(row)))
        clear_cache(self.client_id, self.period)
    monkeypatch.setattr(Medallion, "upsert", write)
    monkeypatch.setattr(pipeline, "GCSObjectStore", Objects)
    for client in ("a", "b"):
        repo.tables.setdefault("gst_client_profile", []).append(Row(client_id=client, gstin="", legal_name="Red Taxi" if client == "a" else "Client B", business_nature="passenger_transport", is_current=True))
    yield repo
    get_settings.cache_clear()
    medallion._cache.clear()


def invoice(**kwargs):
    return {"supplier_gstin": "27AAPFU0939F1ZV", "vendor_name": "Supplier", "invoice_number": "OVERLAP-001", "invoice_date": "2026-09-01", "subtotal": "1000", "total_amount": "1180", "igst": "180", "confidence": "0.99", "line_items": [{"description": "Passenger vehicle", "itc_category": "vehicle", "taxable_value": "1000", "igst": "180"}], **kwargs}


def seed(repo, client):
    store = Medallion(repo, client, "2026-09")
    doc = pipeline.land(store, ("%PDF-1.4 " + client).encode(), "bill.pdf", "application/pdf", client, Objects())
    pipeline.silver(store, doc, invoice(vendor_name=client + " supplier"))
    return store, doc


def test_pipeline_and_deduplication_are_client_scoped(repo):
    a, da = seed(repo, "a")
    b, db = seed(repo, "b")
    assert da["doc_id"] != db["doc_id"]
    repeat = pipeline.land(a, b"%PDF-1.4 a", "renamed.pdf", "application/pdf", "a", Objects())
    assert repeat["duplicate"] and repeat["doc_id"] == da["doc_id"]
    for store, other in ((a, "b"), (b, "a")):
        w = store.workspace()
        assert w["counts"] == {"documents": 1, "review": 0, "posted": 1, "failed": 0}
        assert all(d["client_id"] == store.client_id for d in w["documents"])
        assert other + " supplier" not in medallion.encode(w)
        assert w["documents"][0]["stage"] == "In ledger"
        first = w["summary"]["run_id"]
        assert store.recompute()["run_id"] == first
    for sql, params in repo.queries:
        assert "@client_id" in sql
        assert "client_id" in {p.name for p in params}


def test_eligibility_flip_and_decimal_exactness():
    line = {"itc_category": "vehicle", "invoice_date": "2026-08-10"}
    assert rule(line, {"business_nature": "goods_trader"}) == ("blocked", "17(5)(a)")
    assert rule(line, {"business_nature": "passenger_transport"}) == ("eligible", "17(5)(a)-EXEMPT-PASSENGER-TRANSPORT")
    assert rule({**line, "itc_category": "insurance_repair"}, {"business_nature": "passenger_transport"})[0] == "eligible"
    assert rule({"itc_category": "fuel"}, {}) == ("non_gst", "NON-GST")
    assert amount("0.10") + amount("0.20") == Decimal("0.30")
    with pytest.raises(ValueError):
        amount(0.1)
    assert deadline("2025-04-01") == date(2026, 11, 30)


def test_setoff_respects_heads_and_eco_cash():
    result = set_off({"igst": "100", "cgst": "100", "sgst": "100", "cess": "10"}, {"igst": "150", "cgst": "200", "sgst": "0", "cess": "0"}, {"cgst": "20"})
    assert result["cash_required"] == Decimal("80.00")
    assert result["cash_by_head"]["sgst"] == Decimal("50")
    assert result["cash_by_head"]["cgst"] == Decimal("20")
    assert all((r["from"], r["to"]) not in {( "cgst", "sgst"), ("sgst", "cgst")} for r in result["utilisation"])


def test_common_credit_reversals_and_missing_basis():
    taxes = {h: amount("6000") for h in ('igst', 'cgst', 'sgst', 'cess')}
    profile = {"itc_rule_flags": {"turnover_total": "10000", "turnover_exempt": "2000"}}
    values, ref = common_reversal({"common_credit": True}, profile, taxes)
    assert ref == "R42" and values['igst'] == Decimal('1200.00')
    values, ref = common_reversal({"common_credit": True, "capital_goods": True}, profile, taxes)
    assert ref == "R43" and values['igst'] == Decimal('20.00')
    assert common_reversal({"common_credit": True}, {}, taxes)[1] == "R42-BASIS-MISSING"


def test_ocr_currency_percent_and_ambiguous_amounts():
    data = pipeline.normalise_extraction(invoice(subtotal='INR 1,000.00', gst_rate='18%', confidence='99%'))
    assert not pipeline.validate_extraction(data, '2026-09')
    assert data['subtotal']=='1000.00' and data['gst_rate']=='18.00' and data['confidence']=='0.99'
    bad = pipeline.normalise_extraction(invoice(igst='unclear'))
    assert 'UNREADABLE_IGST' in pipeline.validate_extraction(bad,'2026-09')


@pytest.mark.parametrize("changes,code", [({"supplier_gstin": "INVALID"}, "GSTIN_CHECKSUM"), ({"invoice_date": "2026-01-01"}, "INVOICE_OUTSIDE_PERIOD"), ({"confidence": "0.4"}, "LOW_CONFIDENCE"), ({"cgst": "50"}, "TAX_SPLIT_INCONSISTENT"), ({"gst_rate": "5"}, "TAX_RATE_INCONSISTENT")])
def test_validation(changes, code):
    assert code in pipeline.validate_extraction(invoice(**changes), "2026-09")


def test_filing_permissions_transitions_arn_and_lock(repo):
    store = Medallion(repo, "a", "2026-09")
    client = SimpleNamespace(role="client", email="a@example.test")
    admin = SimpleNamespace(role="tax_admin", email="admin@example.test")
    with pytest.raises(HTTPException) as e:
        workbench.transition(store, client, "locked")
    assert e.value.status_code == 409
    workbench.transition(store, client, "validated")
    workbench.transition(store, client, "json_generated")
    with pytest.raises(HTTPException) as e:
        workbench.transition(store, client, "filed", "A" * 15, "2026-09-20")
    assert e.value.status_code == 403
    with pytest.raises(HTTPException) as e:
        workbench.transition(store, admin, "filed", "bad", "2026-09-20")
    assert e.value.status_code == 422
    workbench.transition(store, admin, "filed", "A" * 15, "2026-09-20")
    workbench.transition(store, admin, "locked")
    with pytest.raises(HTTPException) as e:
        pipeline.land(store, b"%PDF-1.4", "x.pdf", "application/pdf", "a", Objects())
    assert e.value.status_code == 409
    assert len(repo.tables["gst_filing_audit"]) == 4


def test_missing_gstin_blocks_validation(repo):
    store, _ = seed(repo, "a")
    with pytest.raises(HTTPException) as e:
        store.validate_filing()
    assert e.value.status_code == 409
    assert "GSTIN" in e.value.detail


def test_sample_boundary_blocks_before_any_write(repo, monkeypatch):
    monkeypatch.setenv("DEMO_FALLBACK", "true")
    get_settings.cache_clear()
    before = copy.deepcopy(repo.tables)
    for call in (lambda: live_only(), lambda: Medallion(repo, "a", "2026-09").recompute(), lambda: pipeline.land(Medallion(repo, "a", "2026-09"), b"%PDF-1.4", "a.pdf", "application/pdf", "a", Objects())):
        with pytest.raises(HTTPException) as e:
            call()
        assert e.value.status_code == 403
        assert e.value.detail["code"] == "sample_data_blocked"
    assert repo.tables == before


def test_api_cross_client_and_viewer_gates(repo, monkeypatch):
    _, da = seed(repo, "a")
    _, db = seed(repo, "b")
    app = FastAPI()
    app.add_middleware(SessionMiddleware, secret_key="test-only")
    app.include_router(workbench.router)
    app.dependency_overrides[get_db] = lambda: repo
    def identity(request: Request):
        tenant = request.headers.get("x-test-user")
        if not tenant:
            raise HTTPException(401)
        return SimpleNamespace(id=tenant, email=tenant+"@example.test", full_name=tenant, role=request.headers.get("x-test-role", "client"))
    app.dependency_overrides[current_user] = identity
    monkeypatch.setattr(workbench, "active_client", lambda request, repo, user: SimpleNamespace(id=user.id))
    monkeypatch.setattr(workbench.FinanceRepository, "clients", lambda self, user_id: [SimpleNamespace(id=user_id, name=user_id)])
    client = TestClient(app)
    assert client.get('/api/workspace').status_code == 401
    for user, own, other in (("a", da, db), ("b", db, da)):
        headers = {"x-test-user": user}
        for path in ("/api/workspace", "/api/pipeline/search?q=supplier", f"/api/pipeline/documents/{own['doc_id']}"):
            response = client.get(path + ("&" if "?" in path else "?") + "period=2026-09", headers=headers)
            assert response.status_code == 200, response.text
            assert other['doc_id'] not in response.text
        assert client.get(f"/api/pipeline/documents/{other['doc_id']}?period=2026-09", headers=headers).status_code == 404
        for path in ("/api/gst/filing/recompute", "/api/gst/filing/generate/gstr3b", "/api/gst/filing/transition", "/api/gst/filing/import-2b", "/api/gst/filing/outward"):
            response = client.post(path+'?period=2026-09', json={}, headers={**headers,"x-test-role":"viewer"})
            assert response.status_code == 403, (path, response.text)


def test_sql_interpolation_and_money_lint():
    failures = []
    for path in Path('app').rglob('*.py'):
        source = path.read_text(encoding='utf-8')
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.JoinedStr):
                literal = ''.join(n.value for n in node.values if isinstance(n, ast.Constant) and isinstance(n.value,str))
                if re.search(r'\b(SELECT|INSERT|UPDATE|DELETE|MERGE)\b',literal,re.I):
                    for piece in node.values:
                        if isinstance(piece, ast.FormattedValue) and any(isinstance(n,ast.Name) and n.id=='client_id' for n in ast.walk(piece)):
                            failures.append(f'{path}:{node.lineno}: interpolated tenant')
            if isinstance(node,ast.BinOp) and isinstance(node.op,ast.Add):
                if isinstance(node.right,ast.Name) and node.right.id=='client_id':
                    failures.append(f'{path}:{node.lineno}: concatenated tenant')
    assert not failures, '\n'.join(failures)
    for filename in ('rules.py','medallion.py','pipeline.py','workbench.py'):
        tree=ast.parse(Path('app/services/gst',filename).read_text())
        assert not [n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='float']


def test_nav_uses_one_component_and_no_fixture_profile():
    source = Path('frontend/app/workspace.tsx').read_text(encoding='utf-8')
    nav = re.search(r'<nav\b.*?</nav>', source)[0]
    assert '<NavItem' in nav and '<a ' not in nav
    assert '27AAPFU0939F1ZV' not in source and 'Umesh' not in source
    assert 'BigQuery live count' not in source
