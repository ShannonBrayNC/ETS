from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
QUEUE_PATH = ROOT / "config" / "dissertation-work-queue.json"
SCHEMA_PATH = ROOT / "config" / "dissertation-work-queue.schema.json"
SCRIPT_PATH = ROOT / "scripts" / "dissertation_queue.py"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("dissertation_queue", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_queue() -> dict[str, object]:
    return json.loads(QUEUE_PATH.read_text(encoding="utf-8"))


def test_queue_and_schema_are_valid_json() -> None:
    queue = load_queue()
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert queue["$schema"] == "./dissertation-work-queue.schema.json"
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["title"] == "ETS Dissertation Work Queue"


def test_queue_enforces_dissertation_only_hourly_single_task_mode() -> None:
    queue = load_queue()

    assert queue["program"]["mode"] == "dissertation_only"
    assert queue["program"]["other_autonomous_work_paused"] is True
    assert queue["execution"]["cadence"] == "PT1H"
    assert queue["execution"]["max_tasks_per_pass"] == 1
    assert queue["execution"]["allow_overlapping_passes"] is False
    assert queue["execution"]["external_publication_allowed"] is False


def test_semantic_validator_accepts_committed_queue() -> None:
    module = load_script()
    queue = load_queue()

    module.validate_queue(queue)


def test_selector_returns_exactly_one_highest_priority_ready_task() -> None:
    module = load_script()
    queue = load_queue()

    payload = module.selection_payload(queue)

    assert payload["result"] == "selected"
    assert payload["task"]["id"] == "D1-001"


def test_approval_gates_are_not_automation_eligible() -> None:
    queue = load_queue()

    approval_tasks = [task for task in queue["tasks"] if task["approval_required"]]

    assert approval_tasks
    assert all(task["automation_eligible"] is False for task in approval_tasks)
    assert all(task["status"] != "ready" for task in approval_tasks)


def test_validator_rejects_completed_task_without_evidence() -> None:
    module = load_script()
    queue = copy.deepcopy(load_queue())
    queue["tasks"][0]["status"] = "completed"
    queue["tasks"][0]["completion_evidence"] = []

    with pytest.raises(module.QueueValidationError, match="lacks completion evidence"):
        module.validate_queue(queue)


def test_validator_rejects_unknown_dependency() -> None:
    module = load_script()
    queue = copy.deepcopy(load_queue())
    queue["tasks"][3]["dependencies"] = ["D1-999"]

    with pytest.raises(module.QueueValidationError, match="unknown dependency"):
        module.validate_queue(queue)


def test_completed_task_unlocks_promotion_without_automatic_execution() -> None:
    module = load_script()
    queue = copy.deepcopy(load_queue())
    first = next(task for task in queue["tasks"] if task["id"] == "D1-001")
    first["status"] = "completed"
    first["completion_evidence"] = ["https://github.com/ShannonBrayNC/ETS/pull/example"]

    payload = module.selection_payload(queue)

    assert payload["result"] == "promotion_required"
    assert payload["task"]["id"] == "D1-002"


def test_every_task_has_requirement_output_acceptance_and_validation() -> None:
    queue = load_queue()
    requirements = (
        ROOT / "docs" / "requirements" / "ETS_DISSERTATION_PUBLICATION_REQUIREMENTS.md"
    ).read_text(encoding="utf-8")

    for task in queue["tasks"]:
        assert task["requirement_refs"], task["id"]
        assert task["outputs"], task["id"]
        assert task["acceptance_criteria"], task["id"]
        assert task["validation"], task["id"]
        for requirement_id in task["requirement_refs"]:
            assert requirement_id in requirements, (task["id"], requirement_id)
