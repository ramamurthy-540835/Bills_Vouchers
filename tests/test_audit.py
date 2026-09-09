from app.services.audit import log


class R:
    def audit(self, *args):
        return args


def test_audit_delegates_to_bigquery_repository():
    assert log(R(), user_id="u", action="scan", entity="document", entity_id="d") == ("u", "scan", "document", "d")
