from types import SimpleNamespace

import pytest

from app.services import tasks


class Background: 
    def __init__(self):
        self.calls = []

    def add_task(self, callback, *args):
        self.calls.append((callback, args))


def test_dispatch_uses_local_fallback_outside_production(monkeypatch):
    monkeypatch.setattr(tasks, "get_settings", lambda: SimpleNamespace(app_env="development", cloud_tasks_queue="", cloud_tasks_service_url=""))
    background = Background()
    callback = object()
    assert tasks.dispatch_scan(background, callback, "doc", "repo", "user", "client") == "local-background"
    assert background.calls == [(callback, ("doc", "repo", "user", "client"))]


def test_dispatch_requires_cloud_tasks_in_production(monkeypatch):
    monkeypatch.setattr(tasks, "get_settings", lambda: SimpleNamespace(app_env="production", cloud_tasks_queue="", cloud_tasks_service_url=""))
    with pytest.raises(RuntimeError, match="Cloud Tasks is required"):
        tasks.dispatch_scan(Background(), object(), "doc", "repo", "user", "client")


def test_task_callback_rejects_missing_bearer_token():
    request = SimpleNamespace(headers={"x-cloudtasks-queuename": "scan"})
    assert not tasks.verify_cloud_tasks_request(request, "https://service.example", "worker@example.iam.gserviceaccount.com")
