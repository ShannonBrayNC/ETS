from __future__ import annotations

import re
from pathlib import Path

COMPOSE = Path("docker-compose.yml")
EXPECTED_LOOPBACK_PORTS = {
    "127.0.0.1:8101:8000",
    "127.0.0.1:8102:8000",
    "127.0.0.1:8103:8000",
    "127.0.0.1:8201:8000",
    "127.0.0.1:8202:8000",
    "127.0.0.1:8301:8000",
}


def test_federation_demo_publishes_only_loopback_ports() -> None:
    text = COMPOSE.read_text(encoding="utf-8")
    published_ports = set(re.findall(r'^\s+- "([^"\s]+:\d+)"\s*$', text, re.MULTILINE))

    assert published_ports == EXPECTED_LOOPBACK_PORTS
