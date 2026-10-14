"""Shared identity validation. A valid shape is not proof of ownership."""
import re

from fastapi import HTTPException


def registration_mobile(body):
    country = str(body.get('country_code', '+91')).strip()
    number = str(body.get('mobile_number', '')).strip()
    if not re.fullmatch(r'\+[1-9][0-9]{0,2}', country):
        raise HTTPException(422, 'Enter a valid country calling code.')
    if not re.fullmatch(r'[0-9]+', number):
        raise HTTPException(422, 'Enter your mobile number using digits only.')
    full = country + number
    if not re.fullmatch(r'\+[1-9][0-9]{7,14}', full):
        raise HTTPException(422, 'Enter a valid international mobile number.')
    if country == '+91' and not re.fullmatch(r'[6-9][0-9]{9}', number):
        raise HTTPException(422, 'Enter a 10-digit Indian mobile number starting with 6, 7, 8 or 9.')
    return full
