import json
from types import SimpleNamespace
import pytest
from app.services import performance


def test_stage_failure_logs_only_timing_and_not_sensitive_error_text(monkeypatch,caplog):
    monkeypatch.setattr(performance,'get_settings',lambda:SimpleNamespace(performance_metrics_enabled=True))
    with caplog.at_level('INFO',logger=performance.logger.name):
        with pytest.raises(ValueError):
            with performance.measure('invoice_extraction','synthetic-job'):
                raise ValueError('Private invoice contents must never appear in diagnostics')
    record=json.loads(caplog.records[-1].message)
    assert set(record)=={'event','operation','duration_ms','outcome','job_id'}
    assert record['outcome']=='failed' and record['duration_ms']>=0
    assert 'Private invoice contents' not in caplog.text


def test_stage_metrics_are_opt_in_and_preserve_returned_work(monkeypatch,caplog):
    monkeypatch.setattr(performance,'get_settings',lambda:SimpleNamespace())
    with caplog.at_level('INFO',logger=performance.logger.name):
        with performance.measure('invoice_extraction'):
            result='unchanged'
    assert result=='unchanged'
    assert not caplog.records
