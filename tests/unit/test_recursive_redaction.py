from app.core.redaction import mask_object_recursive, mask_secret_value, redact_for_log, redact_for_ui


def test_mask_secret_value_status_only():
    assert mask_secret_value("sk-testsecret123") == "present"
    assert mask_secret_value("") == "missing"


def test_recursive_redaction_masks_keys_and_patterns():
    payload = {"provider": {"api_key": "sk-testsecret123456", "nested": ["Bearer abcdefghijkl"]}}
    redacted = mask_object_recursive(payload)
    assert redacted["provider"]["api_key"] == {"status": "present"}
    assert redacted["provider"]["nested"] == ["[REDACTED]"]
    assert "sk-testsecret" not in str(redact_for_ui(payload))
    assert "abcdefghijkl" not in str(redact_for_log(payload))

