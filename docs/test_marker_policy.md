# Test Marker Policy

## Goal

The local final gate must run only tests that are valid against the local
FastAPI TestClient app. Legacy live HTTP smoke tests are still visible, but
they belong to a separate external-environment gate.

## Markers

- `local_gate`: Included in the local final gate. Failures, errors and skips
  block the local gate.
- `external_env_only`: Requires an external service such as a live backend on
  `localhost:8000`. Excluded from the local final gate.
- `legacy_live_http`: Legacy `httpx` smoke tests against live HTTP endpoints.
  Always paired with `external_env_only`.

## Gate Commands

```powershell
pytest tests/api -m local_gate
pytest tests/api -m external_env_only
```

## Policy

- The local final gate evaluates only `local_gate`.
- Any failed, errored or skipped `local_gate` test blocks the local final gate.
- `external_env_only` skips do not block the local final gate.
- `legacy_live_http` tests must not be silently treated as PASS. They are
  reported separately as the external environment gate.
- New local API tests should use the FastAPI TestClient fixtures from
  `tests/api/conftest.py`.

## Current Legacy Live HTTP Split

The following files are classified as `external_env_only` and
`legacy_live_http`:

- `tests/api/test_gui_backend_endpoints.py`
- `tests/api/test_gui_contracts.py`
- `tests/api/test_gui_secret_masking.py`
- `tests/api/test_secret_masking_api.py`
- `tests/api/test_settings_endpoints.py`
- `tests/api/test_settings_patch.py`
