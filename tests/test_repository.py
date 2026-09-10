from app.repository import FinanceRepository


class FakeBigQuery:
    def __init__(self):
        self.calls = []

    def table(self, name):
        return f"project.dataset.{name}"

    def query(self, sql, params=None):
        self.calls.append(sql)
        if "status=\x27needs_review\x27" in sql:
            return [{"id": "doc-1", "document_type": "bill", "status": "needs_review"}]
        return []

    def one(self, sql, params=None):
        return None


def test_review_queue_uses_named_query_parameters():
    bq = FakeBigQuery()
    items = FinanceRepository(bq).review_documents("client-1", limit=10, offset=20)
    assert [item.id for item in items] == ["doc-1"]
    assert "client_id=@client" in bq.calls[0]
    assert "LIMIT @limit OFFSET @offset" in bq.calls[0]
