"""Backend-only fail-closed gates for integrations outside Method A."""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException


@dataclass(frozen=True)
class ProviderGate:
    name: str
    setting: str


GATES = {
    'gsp': ProviderGate('gsp', 'gst_gsp_enabled'),
    'live_filing': ProviderGate('live_filing', 'gst_live_filing_enabled'),
    'live_gstr2b': ProviderGate('live_gstr2b', 'gst_live_gstr2b_enabled'),
    'official_gstin_lookup': ProviderGate('official_gstin_lookup', 'gst_official_gstin_lookup_enabled'),
    'einvoice': ProviderGate('einvoice', 'gst_einvoice_enabled'),
    'ewaybill': ProviderGate('ewaybill', 'gst_ewaybill_enabled'),
    'external_notifications': ProviderGate('external_notifications', 'gst_external_notifications_enabled'),
}


def enabled(name: str, settings) -> bool:
    """No external adapters are installed in V4; a config flag alone cannot activate one."""
    if name not in GATES:
        raise ValueError('Unknown future provider capability.')
    gate = GATES[name]
    adapter = None  # Intentionally unset until an independently reviewed provider is installed.
    return bool(getattr(settings, gate.setting, False) and adapter is not None)


def require_enabled(name: str, settings) -> None:
    if not enabled(name, settings):
        raise HTTPException(404, 'Not found.')
