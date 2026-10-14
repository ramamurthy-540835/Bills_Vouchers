import pytest
from fastapi import HTTPException

from app.security import hash_password, password_is_strong, verify_password
from app.services.identity_validation import registration_mobile


@pytest.mark.parametrize('password', ['A' * 73, 'Aa1' + 'é' * 35, 'Aa1' + '\ud800' * 12, 'Password123\x00'])
def test_password_encoding_is_rejected_before_hashing(password):
    assert not password_is_strong(password)
    assert not verify_password(password, 'unused')
    with pytest.raises(ValueError):
        hash_password(password)


def test_password_boundary_round_trip():
    password = 'Aa1' + 'x' * 69
    assert password_is_strong(password)
    assert verify_password(password, hash_password(password))


@pytest.mark.parametrize('body', [{}, {'mobile_number':'1234567890'}, {'mobile_number':'987654321'}, {'country_code':'+91','mobile_number':'９８７６５４３２１０'}, {'country_code':'+1234','mobile_number':'9876543210'}])
def test_invalid_registration_mobile(body):
    with pytest.raises(HTTPException):
        registration_mobile(body)


def test_mobile_country_validation():
    assert registration_mobile({'mobile_number':'9876543210'}) == '+919876543210'
    assert registration_mobile({'country_code':'+44','mobile_number':'7700900000'}) == '+447700900000'
