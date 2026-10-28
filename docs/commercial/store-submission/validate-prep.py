"""Validate this preparation folder; never submit or mark a release approved."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def read_json(relative: str) -> dict:
    value = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    assert isinstance(value, dict), relative
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-ready", action="store_true")
    args = parser.parse_args()
    listing = read_json("listing/en-us.json")
    assert listing["schema"] == "ets.store_listing_draft.v1"
    assert listing["status"] == "draft_owner_review_required"
    assert listing["language"] == "en-us"
    limits = {"product_name_proposal": 256, "short_description": 1000,
              "description": 10000, "whats_new": 1500}
    for field, maximum in limits.items():
        assert isinstance(listing[field], str)
        assert len(listing[field]) <= maximum, field
    assert listing["description"] and len(listing["short_description"]) < 270
    assert not re.search(r"https?://|<[^>]+>", listing["description"])
    assert listing["whats_new"] == "", "First submission must leave What's new blank"
    for field, count, size in [("features", 20, 200), ("keywords", 7, 40),
                               ("minimum_requirements", 11, 200),
                               ("recommended_requirements", 11, 200)]:
        values = listing[field]
        assert isinstance(values, list) and len(values) <= count, field
        assert all(isinstance(v, str) and 0 < len(v) <= size for v in values), field
    assert sum(len(term.split()) for term in listing["keywords"]) <= 21
    copy = (ROOT / "listing/COPY-READY.txt").read_text(encoding="utf-8")
    for field in ["product_name_proposal", "short_description", "description"]:
        assert listing[field] in copy, f"Copy-ready draft differs: {field}"
    assert all(v in copy for v in listing["features"] + listing["keywords"])

    owner = read_json("OWNER-DECISIONS.json")
    assert owner["schema"] == "ets.store_owner_decisions.v1"
    assert owner["not_a_partner_center_payload"] is True
    assert len(owner["decisions"]) >= 20
    assert all(isinstance(v, bool) for v in owner["release_gates"].values())
    blockers = ["Owner decision: " + k for k, v in owner["decisions"].items()
                if v is None or v == "" or v == []]
    blockers += ["Release gate: " + k for k, v in owner["release_gates"].items() if not v]

    assets = read_json("assets/ASSET-MANIFEST.json")
    assert assets["schema"] == "ets.store_assets_draft.v1"
    assert len(assets["shot_list"]) <= 10
    for shot in assets["shot_list"]:
        assert len(shot["caption"]) <= 200
    if not assets["approved_upload_files"]:
        blockers.append("No approved native screenshot/icon files")
    for item in assets["approved_upload_files"]:
        path = (ROOT / "assets" / item["filename"]).resolve()
        assert path.is_relative_to((ROOT / "assets").resolve())
        payload = path.read_bytes()
        assert payload[:8] == b"\x89PNG\r\n\x1a\n" and len(payload) <= 50000000
        assert hashlib.sha256(payload).hexdigest() == item["sha256"]
        width, height = struct.unpack(">II", payload[16:24])
        if item["kind"] == "desktop_screenshot":
            assert width >= 1366 and height >= 768
        elif item["kind"] == "store_icon":
            assert (width, height) == (300, 300)
        else:
            raise AssertionError("Unknown asset kind")

    sample = ROOT / "fixtures/synthetic-sample"
    summary = read_json("fixtures/synthetic-sample/sample-summary.json")
    assert summary["schema"] == "ets.desktop_synthetic_sample.v1"
    assert summary["synthetic_only"] and summary["creation_complete"]
    assert summary["private_key_saved"] is False
    assert summary["expected_log_id"] == "ets-desktop-synthetic"
    assert len(summary["sha256"]) == 6
    for filename, digest in summary["sha256"].items():
        assert Path(filename).name == filename
        assert hashlib.sha256((sample / filename).read_bytes()).hexdigest() == digest
    assert set(p.name for p in sample.iterdir()) == set(summary["sha256"]) | {"sample-summary.json"}
    for case, status, code in [("missing-trust", "indeterminate", 2),
                               ("selected-trust", "valid", 0),
                               ("wrong-log", "invalid", 1),
                               ("tampered", "invalid", 1)]:
        result = read_json(f"evidence/fixture-{case}.json")
        assert result["case"] == case and result["exit_code"] == code
        outcome = result["outcome"]
        assert outcome["status"] == status and outcome["valid"] == (status == "valid")
        if status == "valid":
            assert outcome["signature_verified"] is True
            assert outcome["continuity_verified"] is False
            assert outcome["standing_status"] == "checkpoint_only"

    qualification = read_json("evidence/preview-qualification.json")
    assert qualification["identity"] == "ETSDeveloper.Development"
    assert qualification["signed"] is False and qualification["releaseApproved"] is False
    assert qualification["wackPassed"] is False
    candidate = read_json("evidence/preview-candidate.json")
    assert candidate["sourceSha"] == "2606424f61a8791bb1afc8169629f8390e849def"
    assert candidate["releaseApproved"] is False
    provenance = read_json("evidence/PREPARATION-PROVENANCE.json")
    assert provenance["fixture_private_key_saved"] is False
    assert provenance["store_submission_performed"] is False

    local_links = 0
    for path in ROOT.rglob("*.md"):
        for target in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            if "://" in target or target.startswith("#"):
                continue
            target = target.split("#", 1)[0]
            assert (path.parent / target).exists(), f"Broken link: {path.name}: {target}"
            local_links += 1
    print(json.dumps({"preparation_checks": "passed", "local_links_checked": local_links,
                      "listing_characters": {k: len(listing[k]) for k in limits},
                      "keyword_words": sum(len(t.split()) for t in listing["keywords"]),
                      "synthetic_fixture_cases": 4, "unresolved_gates": len(blockers),
                      "release_ready": not blockers}, indent=2))
    if args.require_ready and blockers:
        print("NOT READY:\n" + "\n".join(blockers))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
