import pytest

from ets.core.canonical_json import CanonicalJSONError, canonical_sha256, canonicalize


def test_canonicalize_sorts_keys_without_whitespace():
    assert canonicalize({"b": 2, "a": 1}) == b'{"a":1,"b":2}'


def test_canonical_sha256_is_stable_for_reordered_keys():
    left = {"event": {"b": [2, None], "a": "value"}}
    right = {"event": {"a": "value", "b": [2, None]}}

    assert canonical_sha256(left) == canonical_sha256(right)


def test_canonical_sha256_changes_when_value_changes():
    assert canonical_sha256({"a": 1}) != canonical_sha256({"a": 2})


def test_canonicalize_preserves_unicode_as_utf8():
    assert canonicalize({"name": "café"}).decode("utf-8") == '{"name":"café"}'


@pytest.mark.parametrize("value", [float("nan"), float("inf"), {"bad": object()}, {1: "x"}, (1, 2)])
def test_canonicalize_rejects_non_json_native_values(value):
    with pytest.raises(CanonicalJSONError):
        canonicalize(value)
