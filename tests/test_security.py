from app.security import hash_password, login_allowed, password_is_strong, record_login_failure, record_login_success, same_origin, verify_password


def test_password_policy():
    assert password_is_strong("Strong-password-123")
    assert not password_is_strong("short1A")
    assert not password_is_strong("lowercase-password-1")


def test_passwords_are_hashed_and_verified():
    encoded = hash_password("A-long-password-123")
    assert encoded != "A-long-password-123"
    assert verify_password("A-long-password-123", encoded)
    assert not verify_password("wrong", encoded)


def test_login_throttle_resets_after_success():
    key = "test-rate-limit-unique"
    for _ in range(5):
        record_login_failure(key)
    assert not login_allowed(key)
    record_login_success(key)
    assert login_allowed(key)


def test_same_origin_accepts_full_referer_path():
    assert same_origin("https://bills-voucher.example/documents/upload", "https://bills-voucher.example/")
    assert not same_origin("https://untrusted.example/documents/upload", "https://bills-voucher.example/")



def test_mcp_sql_guard_rejects_writes():
    from app.services.mcp_server import validate_read_only_sql
    assert validate_read_only_sql("SELECT 1;") == "SELECT 1"
    for statement in ("SELECT 1; DELETE FROM t", "WITH x AS (SELECT 1) DELETE FROM t", "UPDATE t SET x=1"):
        try:
            validate_read_only_sql(statement)
        except ValueError:
            pass
        else:
            raise AssertionError("write query was accepted")


def test_last_admin_cannot_be_removed():
    from fastapi import HTTPException
    from app.models import Role, ns
    from app.routes import assert_not_last_admin

    class Repo:
        def table(self, name):
            return name

        def one(self, sql, params):
            return ns(n=0)

    try:
        assert_not_last_admin(Repo(), ns(id="admin-1", role="admin", is_active=True), Role.ACCOUNTANT, True)
    except HTTPException as exc:
        assert exc.status_code == 400
        assert "last active Admin" in str(exc.detail)
    else:
        raise AssertionError("last admin change was accepted")


def test_admin_change_allowed_when_another_admin_exists():
    from app.models import Role, ns
    from app.routes import assert_not_last_admin

    class Repo:
        def table(self, name):
            return name

        def one(self, sql, params):
            return ns(n=1)

    assert_not_last_admin(Repo(), ns(id="admin-1", role="admin", is_active=True), Role.ACCOUNTANT, True)
