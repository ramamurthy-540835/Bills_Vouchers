from collections import defaultdict
from threading import Lock
from time import monotonic

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_login_failures: dict[str, list[float]] = defaultdict(list)
_login_lock = Lock()
_WINDOW_SECONDS = 300
_MAX_FAILURES = 5


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def login_allowed(key: str) -> bool:
    now = monotonic()
    with _login_lock:
        _login_failures[key] = [stamp for stamp in _login_failures[key] if now - stamp < _WINDOW_SECONDS]
        return len(_login_failures[key]) < _MAX_FAILURES


def record_login_failure(key: str) -> None:
    with _login_lock:
        _login_failures[key].append(monotonic())


def record_login_success(key: str) -> None:
    with _login_lock:
        _login_failures.pop(key, None)
