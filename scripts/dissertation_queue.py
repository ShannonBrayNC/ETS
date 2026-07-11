#!/usr/bin/env python3
"""Validate and select work from the ETS dissertation queue.

This script is intentionally read-only. Repository automation owns status and
completion-evidence updates through reviewed commits. Keeping selection read-only
prevents an hourly heartbeat from silently claiming that scholarly work is done.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUEUE = ROOT / "config" / "dissertation-work-queue.json"
VALID_RISKS = {"low", "medium", "high", "critical", "approval_gate"}


class QueueValidationError(ValueError):
    """Raised when the dissertation queue violates its execution contract."""


def load_queue(path: Path) -> dict[str, Any]:
    """Load a UTF-8 JSON queue and require an object at the root."""

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise QueueValidationError(f"queue file does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise QueueValidationError(f"queue is not valid JSON: {exc}") from exc

    if not isinstance(value, dict):
        raise QueueValidationError("queue root must be a JSON object")
    return value


def require_fields(value: dict[str, Any], fields: Iterable[str], context: str) -> None:
    """Require all named fields in one object."""

    missing = sorted(set(fields) - value.keys())
    if missing:
        raise QueueValidationError(f"{context} is missing fields: {', '.join(missing)}")


def validate_queue(queue: dict[str, Any]) -> None:
    """Validate structure, dependency safety, and scholarly completion controls."""

    require_fields(
        queue,
        {"schema_version", "program", "execution", "allowed_statuses", "sprints", "tasks"},
        "queue",
    )
    if queue["schema_version"] != "ets.dissertation.queue.v1":
        raise QueueValidationError("unsupported schema_version")

    program = queue["program"]
    execution = queue["execution"]
    sprints = queue["sprints"]
    tasks = queue["tasks"]
    statuses = set(queue["allowed_statuses"])

    if not isinstance(program, dict) or not isinstance(execution, dict):
        raise QueueValidationError("program and execution must be objects")
    if program.get("repository") != "ShannonBrayNC/ETS":
        raise QueueValidationError("queue repository must be ShannonBrayNC/ETS")
    if program.get("mode") != "dissertation_only":
        raise QueueValidationError("program mode must remain dissertation_only")
    if program.get("other_autonomous_work_paused") is not True:
        raise QueueValidationError("other autonomous work must remain paused")
    if execution.get("cadence") != "PT1H" or execution.get("max_tasks_per_pass") != 1:
        raise QueueValidationError("execution must select exactly one task per hourly pass")
    if execution.get("allow_overlapping_passes") is not False:
        raise QueueValidationError("overlapping dissertation passes are forbidden")
    if execution.get("completion_requires_evidence") is not True:
        raise QueueValidationError("completion must require evidence")
    if execution.get("external_publication_allowed") is not False:
        raise QueueValidationError("external publication must remain approval-gated")

    if not isinstance(sprints, list) or not isinstance(tasks, list):
        raise QueueValidationError("sprints and tasks must be arrays")
    if not isinstance(statuses, set) or not statuses:
        raise QueueValidationError("allowed_statuses must not be empty")

    sprint_ids: set[str] = set()
    sprint_orders: set[int] = set()
    sprint_order: dict[str, int] = {}
    for sprint in sprints:
        if not isinstance(sprint, dict):
            raise QueueValidationError("every sprint must be an object")
        require_fields(sprint, {"id", "order", "name"}, "sprint")
        sprint_id = sprint["id"]
        order = sprint["order"]
        if sprint_id in sprint_ids or order in sprint_orders:
            raise QueueValidationError(f"duplicate sprint id or order: {sprint_id}/{order}")
        sprint_ids.add(sprint_id)
        sprint_orders.add(order)
        sprint_order[sprint_id] = order

    if program.get("active_sprint") not in sprint_ids:
        raise QueueValidationError("active_sprint does not exist")

    required_task_fields = {
        "id",
        "sprint",
        "task_order",
        "priority",
        "title",
        "status",
        "automation_eligible",
        "approval_required",
        "dependencies",
        "issue_refs",
        "requirement_refs",
        "outputs",
        "acceptance_criteria",
        "validation",
        "claim_risk",
        "completion_evidence",
    }
    task_by_id: dict[str, dict[str, Any]] = {}
    ordering_keys: set[tuple[str, int]] = set()
    for task in tasks:
        if not isinstance(task, dict):
            raise QueueValidationError("every task must be an object")
        require_fields(task, required_task_fields, f"task {task.get('id', '<unknown>')}")
        task_id = task["id"]
        sprint_id = task["sprint"]
        if task_id in task_by_id:
            raise QueueValidationError(f"duplicate task id: {task_id}")
        if sprint_id not in sprint_ids or not task_id.startswith(f"{sprint_id}-"):
            raise QueueValidationError(f"task {task_id} has invalid sprint {sprint_id}")
        ordering_key = (sprint_id, task["task_order"])
        if ordering_key in ordering_keys:
            raise QueueValidationError(f"duplicate task order in sprint: {ordering_key}")
        ordering_keys.add(ordering_key)
        if task["status"] not in statuses:
            raise QueueValidationError(f"task {task_id} has invalid status")
        if task["claim_risk"] not in VALID_RISKS:
            raise QueueValidationError(f"task {task_id} has invalid claim_risk")
        if not task["outputs"] or not task["acceptance_criteria"] or not task["validation"]:
            raise QueueValidationError(f"task {task_id} lacks output, acceptance, or validation")
        if task["approval_required"] and task["automation_eligible"]:
            raise QueueValidationError(
                f"task {task_id} cannot be automation-eligible while approval is required"
            )
        if task["status"] == "completed" and not task["completion_evidence"]:
            raise QueueValidationError(f"completed task {task_id} lacks completion evidence")
        if task["status"] == "ready" and not task["automation_eligible"]:
            raise QueueValidationError(f"non-automatable task {task_id} cannot be ready")
        task_by_id[task_id] = task

    for task_id, task in task_by_id.items():
        dependencies = task["dependencies"]
        if len(dependencies) != len(set(dependencies)):
            raise QueueValidationError(f"task {task_id} has duplicate dependencies")
        for dependency in dependencies:
            if dependency not in task_by_id:
                raise QueueValidationError(f"task {task_id} has unknown dependency {dependency}")
            if dependency == task_id:
                raise QueueValidationError(f"task {task_id} depends on itself")
            if sprint_order[task_by_id[dependency]["sprint"]] > sprint_order[task["sprint"]]:
                raise QueueValidationError(f"task {task_id} depends on a later sprint {dependency}")

    _validate_acyclic(task_by_id)


def _validate_acyclic(task_by_id: dict[str, dict[str, Any]]) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str) -> None:
        if task_id in visited:
            return
        if task_id in visiting:
            raise QueueValidationError(f"dependency cycle detected at {task_id}")
        visiting.add(task_id)
        for dependency in task_by_id[task_id]["dependencies"]:
            visit(dependency)
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in task_by_id:
        visit(task_id)


def ready_tasks(queue: dict[str, Any]) -> list[dict[str, Any]]:
    """Return ready, automation-safe tasks whose dependencies are completed."""

    validate_queue(queue)
    tasks = queue["tasks"]
    task_by_id = {task["id"]: task for task in tasks}
    sprint_order = {sprint["id"]: sprint["order"] for sprint in queue["sprints"]}

    ready = []
    for task in tasks:
        if task["status"] != "ready":
            continue
        if not task["automation_eligible"] or task["approval_required"]:
            continue
        if all(task_by_id[item]["status"] == "completed" for item in task["dependencies"]):
            ready.append(task)

    return sorted(
        ready,
        key=lambda task: (
            task["priority"],
            sprint_order[task["sprint"]],
            task["task_order"],
            task["id"],
        ),
    )


def promotable_tasks(queue: dict[str, Any]) -> list[dict[str, Any]]:
    """Return planned tasks whose dependencies are complete.

    This does not mutate the queue. An implementation pass may promote only the
    first returned task after reviewing blockers and duplicate work.
    """

    validate_queue(queue)
    tasks = queue["tasks"]
    task_by_id = {task["id"]: task for task in tasks}
    sprint_order = {sprint["id"]: sprint["order"] for sprint in queue["sprints"]}
    candidates = [
        task
        for task in tasks
        if task["status"] == "planned"
        and task["automation_eligible"]
        and not task["approval_required"]
        and all(task_by_id[item]["status"] == "completed" for item in task["dependencies"])
    ]
    return sorted(
        candidates,
        key=lambda task: (
            task["priority"],
            sprint_order[task["sprint"]],
            task["task_order"],
            task["id"],
        ),
    )


def selection_payload(queue: dict[str, Any]) -> dict[str, Any]:
    """Return one selected task or a deterministic blocked/no-ready result."""

    ready = ready_tasks(queue)
    if ready:
        return {"result": "selected", "task": ready[0]}

    promotable = promotable_tasks(queue)
    if promotable:
        return {
            "result": "promotion_required",
            "task": promotable[0],
            "message": "Promote this task to ready in a reviewed queue update before execution.",
        }

    blocked = [task for task in queue["tasks"] if task["status"] in {"blocked", "human_review"}]
    return {
        "result": "no_ready_task",
        "blocked_tasks": [task["id"] for task in blocked],
        "message": "No automation-eligible task is ready; do not invent substitute work.",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate", "next", "summary"))
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        queue = load_queue(args.queue)
        validate_queue(queue)
        if args.command == "validate":
            payload: dict[str, Any] = {
                "result": "valid",
                "tasks": len(queue["tasks"]),
                "sprints": len(queue["sprints"]),
            }
        elif args.command == "next":
            payload = selection_payload(queue)
        else:
            counts: dict[str, int] = {}
            for task in queue["tasks"]:
                counts[task["status"]] = counts.get(task["status"], 0) + 1
            payload = {"result": "summary", "counts": counts, "next": selection_payload(queue)}
    except QueueValidationError as exc:
        print(f"dissertation queue validation failed: {exc}", file=sys.stderr)
        return 1

    if args.json or args.command != "validate":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"valid: {payload['tasks']} tasks across {payload['sprints']} sprints")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
