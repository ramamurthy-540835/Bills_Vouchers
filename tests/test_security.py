from app.security import hash_password, login_allowed, record_login_failure, record_login_success, same_origin, verify_password


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
    assert same_origin(
        "https://bills-voucher-foovqasysa-el.a.run.app/documents/upload",
        "https://bills-voucher-foovqasysa-el.a.run.app/",
    )
    assert not same_origin("https://untrusted.example/documents/upload", "https://bills-voucher.example/")


def test_same_origin_accepts_configured_public_origin():
    assert same_origin(
        "https://bills-voucher-foovqasysa-el.a.run.app",
        "https://bills-voucher-foovqasysa-el.a.run.app",
    )
