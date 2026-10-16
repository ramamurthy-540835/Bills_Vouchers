"""Reviewed adapters only. No portal scraping or generic user-controlled HTTP target."""
from typing import Callable, Protocol, Literal
import re

from pydantic import BaseModel, ConfigDict, Field


class ProviderRecord(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    gstin: str = Field(min_length=15, max_length=15)
    found: bool
    registration_status: Literal['active', 'cancelled', 'suspended', 'inactive', 'unknown']
    legal_name: str = Field(default='', max_length=500)
    trade_name: str = Field(default='', max_length=500)
    address: str = Field(default='', max_length=2000)
    registration_type: str = Field(default='', max_length=100)
    registration_date: str = Field(default='', max_length=40)
    reference: str = Field(default='', max_length=200)


class ProviderFailure(Exception):
    """Only safe codes cross the provider boundary; never raw responses or credentials."""
    def __init__(self, code: str):
        self.code = code if code in {'timeout', 'rate_limited', 'unavailable', 'invalid_response', 'credentials_unavailable'} else 'unavailable'
        super().__init__(self.code)


class TaxpayerProvider(Protocol):
    def lookup(self, gstin: str, *, timeout_seconds: int) -> ProviderRecord: ...


# Deliberately empty until an approved provider contract and access are supplied.
# Adapters must enforce the supplied timeout, disable redirects/retries, bound payloads,
# map vendor-specific responses, and return only validated ProviderRecord values.
ADAPTERS: dict[str, Callable[[str], TaxpayerProvider]] = {}


def integration(settings):
    mode = settings.gst_verification_mode
    if mode != 'gsp':
        return None, 'manual' if mode == 'manual' else 'unavailable'
    if not (settings.gst_verification_live_enabled and settings.gst_verification_storage_enabled
            and settings.gst_verification_provider in ADAPTERS):
        return None, 'unavailable'
    secret = settings.gst_verification_secret_version
    if not re.fullmatch(r'projects/[^/]+/secrets/[^/]+/versions/[0-9]+', secret):
        return None, 'unavailable'
    try:
        from google.cloud import secretmanager
        response = secretmanager.SecretManagerServiceClient().access_secret_version(
            request={'name': secret}, timeout=5, retry=None)
        credentials = response.payload.data.decode('utf-8')
        if not credentials or len(credentials) > 65536:
            return None, 'unavailable'
        return ADAPTERS[settings.gst_verification_provider](credentials), 'gsp'
    except Exception:
        # Never expose Secret Manager or vendor exception text to logs/responses.
        return None, 'unavailable'
