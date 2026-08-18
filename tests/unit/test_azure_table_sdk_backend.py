from __future__ import annotations

from collections.abc import ItemsView
from typing import cast

import pytest

from ets.core.azure_table_store import AzureSdkTableBackend
from ets.core.storage import StorageValidationError


class _Entity:
    def __init__(self, metadata: object) -> None:
        self.metadata = metadata
        self._values: dict[str, object] = {
            "PartitionKey": "partition",
            "RowKey": "row",
            "kind": "metadata",
        }

    def items(self) -> ItemsView[str, object]:
        return self._values.items()


class _MetadataObject:
    def __init__(self, etag: object) -> None:
        self.etag = etag


class _Client:
    def __init__(self, entity: _Entity) -> None:
        self._entity = entity

    def get_entity(self, partition_key: str, row_key: str) -> _Entity:
        assert partition_key == "partition"
        assert row_key == "row"
        return self._entity


def _backend(entity: _Entity) -> AzureSdkTableBackend:
    backend = object.__new__(AzureSdkTableBackend)
    backend._client = cast(object, _Client(entity))  # type: ignore[assignment]
    return backend


@pytest.mark.parametrize(
    ("metadata", "expected_etag"),
    [
        ({"etag": 'W/"mapping"'}, 'W/"mapping"'),
        (_MetadataObject('W/"attribute"'), 'W/"attribute"'),
    ],
)
def test_get_accepts_sdk_mapping_and_attribute_metadata(
    metadata: object,
    expected_etag: str,
) -> None:
    result = _backend(_Entity(metadata)).get("partition", "row")

    assert result is not None
    assert result.etag == expected_etag
    assert result.values["kind"] == "metadata"


@pytest.mark.parametrize("metadata", [{}, {"etag": None}, _MetadataObject(None)])
def test_get_rejects_missing_or_invalid_sdk_etag(metadata: object) -> None:
    with pytest.raises(StorageValidationError, match="ETag is missing"):
        _backend(_Entity(metadata)).get("partition", "row")
