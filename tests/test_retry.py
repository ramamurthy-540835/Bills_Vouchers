from app.services.retry import retry_call


def test_retry_call_retries_then_returns(monkeypatch):
    calls = {"count": 0}

    def operation():
        calls["count"] += 1
        if calls["count"] < 3:
            raise TimeoutError("temporary")
        return "ok"

    monkeypatch.setattr("app.services.retry.time.sleep", lambda _: None)
    assert retry_call(operation, attempts=3) == "ok"
    assert calls["count"] == 3
