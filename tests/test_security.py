from app.security import hash_password, verify_password

def test_passwords_are_hashed_and_verified():
    encoded=hash_password("A-long-password-123")
    assert encoded != "A-long-password-123"
    assert verify_password("A-long-password-123",encoded)
    assert not verify_password("wrong",encoded)
