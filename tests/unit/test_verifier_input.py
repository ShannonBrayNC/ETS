from __future__ import annotations

import io
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from ets.verifier.cli import main
from ets.verifier.input import InputLimitError, read_json


@pytest.mark.parametrize(
    "raw",
    [
        b'{"a":1,"a":2}',
        b'{"a":{"b":1,"b":2}}',
        b'{"a":NaN}',
        b'{"a":Infinity}',
        b'{"a":-Infinity}',
        b'{"a":1e999}',
        b'{"a":"\\ud800"}',
        b'{"\\udfff":1}',
        b'{"a":"\xff"}',
        b"\xef\xbb\xbf{}",
        b"{}{}",
        b"{",
    ],
)
def test_rejects_ambiguous_or_invalid_json(tmp_path, raw):
    path = tmp_path / "input.json"
    path.write_bytes(raw)
    with pytest.raises(ValueError):
        read_json(path)


def test_reads_only_limit_plus_one_without_stat():
    stream = io.BytesIO(b" " * 100)
    opened = Mock()
    opened.__enter__ = Mock(return_value=stream)
    opened.__exit__ = Mock(return_value=False)
    path = Mock(spec=Path)
    path.open.return_value = opened
    with pytest.raises(InputLimitError):
        read_json(path, 10)
    assert stream.tell() == 11
    path.stat.assert_not_called()


def test_exact_byte_limit_is_accepted(tmp_path):
    path = tmp_path / "input.json"
    path.write_bytes(b'{"a":1}')
    assert read_json(path, 7) == {"a": 1}
    with pytest.raises(InputLimitError):
        read_json(path, 6)


def test_nesting_limit_precedes_parser(tmp_path):
    path = tmp_path / "input.json"
    path.write_text("[" * 64 + "0" + "]" * 64)
    assert isinstance(read_json(path), list)
    path.write_text("[" * 65 + "0" + "]" * 65)
    with pytest.raises(InputLimitError):
        read_json(path)
    path.write_text(json.dumps({"quoted": '[{"escaped": "\\"}]' * 100}))
    assert read_json(path)["quoted"]


def test_item_limit(tmp_path):
    path = tmp_path / "input.json"
    path.write_text(json.dumps([0] * 100_000))
    with pytest.raises(InputLimitError):
        read_json(path)


def test_valid_unicode_and_whitespace(tmp_path):
    path = tmp_path / "input.json"
    path.write_text(' {"text":"\\ud83d\\ude00", "number":1.25} \n')
    assert read_json(path) == {"text": "😀", "number": 1.25}


def test_cli_limit_has_machine_readable_status(tmp_path, capsys):
    path = tmp_path / "input.json"
    path.write_text("[" * 65 + "0" + "]" * 65)
    assert main(["offline", str(path)]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "resource_limit"


def test_cli_schema_errors_do_not_echo_artifact_data(tmp_path, capsys):
    path = tmp_path / "input.json"
    path.write_text('{"sensitive":"do-not-echo-this"}')
    assert main(["offline", str(path)]) == 2
    output = capsys.readouterr().out
    assert "do-not-echo-this" not in output
    assert json.loads(output)["status"] == "malformed"
