from typing import Any, Callable

from ..config import get_settings


def dispatch_scan(background_tasks: Any, callback: Callable[..., Any], document_id: str, repo: Any, user_id: str, client_id: str) -> str:
    settings = get_settings()
    if settings.cloud_tasks_queue and settings.cloud_tasks_service_url:
        try:
            return enqueue_scan(document_id, settings.cloud_tasks_service_url, settings.cloud_tasks_queue, settings.cloud_tasks_service_account, client_id, user_id)
        except Exception:
            if settings.app_env == "production":
                raise
    elif settings.app_env == "production":
        raise RuntimeError("Cloud Tasks is required in production scan mode.")
    background_tasks.add_task(callback, document_id, repo, user_id, client_id)
    return "local-background"


def enqueue_scan(document_id: str, service_url: str, queue_path: str, service_account: str = "", client_id: str = "", user_id: str = "") -> str:
    from google.cloud import tasks_v2  # type: ignore[attr-defined]

    client = tasks_v2.CloudTasksClient()
    payload = {"document_id": document_id, "client_id": client_id, "user_id": user_id}
    task: dict[str, Any] = {
        "http_request": {
            "http_method": tasks_v2.HttpMethod.POST,
            "url": f"{service_url.rstrip(chr(47))}/internal/tasks/scan",
            "headers": {"Content-Type": "application/json"},
            "body": __import__("json").dumps(payload).encode(),
        }
    }
    if service_account:
        task["http_request"]["oidc_token"] = {"service_account_email": service_account, "audience": service_url}
    created = client.create_task(request={"parent": queue_path, "task": task})
    return created.name


def verify_cloud_tasks_request(request: Any, service_url: str, service_account: str) -> bool:
    """Verify the Cloud Tasks OIDC token; diagnostic queue headers are not auth."""
    authorization = str(request.headers.get("authorization", ""))
    if not authorization.lower().startswith("bearer "):
        return False
    token = authorization.split(" ", 1)[1].strip()
    if not token or not service_url or not service_account:
        return False
    try:
        from google.auth.transport.requests import Request
        from google.oauth2 import id_token

        claims = id_token.verify_oauth2_token(token, Request(), audience=service_url)
        return str(claims.get("email", "")).lower() == service_account.lower()
    except Exception:
        return False
