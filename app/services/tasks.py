"""Optional Cloud Tasks adapter with a local fallback at the caller."""

from typing import Any, Callable

from ..config import get_settings


def dispatch_scan(background_tasks: Any, callback: Callable[..., Any], document_id: str, repo: Any, user_id: str, client_id: str) -> None:
    settings = get_settings()
    if settings.cloud_tasks_queue and settings.cloud_tasks_service_url:
        try:
            enqueue_scan(document_id, settings.cloud_tasks_service_url, settings.cloud_tasks_queue, settings.cloud_tasks_service_account, client_id, user_id)
            return
        except Exception:
            pass
    background_tasks.add_task(callback, document_id, repo, user_id, client_id)


def enqueue_scan(document_id: str, service_url: str, queue_path: str, service_account: str = "", client_id: str = "", user_id: str = "") -> str:
    from google.cloud import tasks_v2  # type: ignore[attr-defined]

    client = tasks_v2.CloudTasksClient()
    parent = queue_path
    payload = {"document_id": document_id, "client_id": client_id, "user_id": user_id}
    task: dict[str, Any] = {
        "http_request": {
            "http_method": tasks_v2.HttpMethod.POST,
            "url": f"{service_url.rstrip('/')}/internal/tasks/scan",
            "headers": {"Content-Type": "application/json"},
            "body": __import__("json").dumps(payload).encode(),
        }
    }
    if service_account:
        task["http_request"]["oidc_token"] = {"service_account_email": service_account, "audience": service_url}
    created = client.create_task(request={"parent": parent, "task": task})
    return created.name
