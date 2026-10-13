"""Chess Academy-style ETS SDK walkthrough for the local ETS Dev profile."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from uuid import uuid4

from ets.core import canonical_sha256
from ets.sdk import ETSClient
from ets.verifier.service import VerifierPolicy

INITIAL_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
MOVES = (
    (
        "e4",
        "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
    ),
    (
        "e5",
        "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
    ),
    (
        "Nf3",
        "rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2",
    ),
    (
        "Nc6",
        "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3",
    ),
)


def _state_hash(fen: str) -> str:
    return canonical_sha256({"fen": fen})


def _event(
    *,
    game_id: str,
    ply: int,
    move: str,
    prior_fen: str,
    resulting_fen: str,
) -> dict[str, object]:
    observation = {
        "game_id": game_id,
        "ply": ply,
        "move": move,
        "prior_state_hash": _state_hash(prior_fen),
        "resulting_state_hash": _state_hash(resulting_fen),
        "resulting_fen": resulting_fen,
    }
    event_id = f"chess-{game_id}-ply-{ply:02d}"
    return {
        "event_id": event_id,
        "tenant_id": "dev-tenant",
        "workspace_id": "chess-academy",
        "evidence_id": f"evidence-{event_id}",
        "event_type": "game.move",
        "subject_ref": f"chess-game:{game_id}",
        "content_hash": canonical_sha256(observation),
        "content_hash_alg": "sha256",
        "metadata": {"observation": observation},
        "created_at_utc": datetime.now(UTC),
        "source_system": "chess-academy-sdk-walkthrough",
        "actor_id": "sample-player",
        "correlation_id": game_id,
        "external_refs": None,
        "redaction_profile": None,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    game_id = uuid4().hex[:12]
    prior_fen = INITIAL_FEN
    final_event_id = ""

    with ETSClient(
        args.endpoint,
        tenant_id="dev-tenant",
        workspace_id="chess-academy",
        allow_insecure_http=True,
    ) as ets:
        version = ets.check_compatibility()

        for ply, (move, resulting_fen) in enumerate(MOVES, start=1):
            event = _event(
                game_id=game_id,
                ply=ply,
                move=move,
                prior_fen=prior_fen,
                resulting_fen=resulting_fen,
            )
            receipt = ets.capture(event)
            if receipt.commitment_state != "committed_local":
                raise RuntimeError("unexpected ETS commitment state")
            final_event_id = receipt.event_id
            prior_fen = resulting_fen

        bundle = ets.bundle(final_event_id)
        policy = VerifierPolicy(require_tree_head_signature=False)
        verified = ets.verify_offline(bundle, policy=policy)
        if not verified.valid:
            raise RuntimeError(f"expected valid bundle: {verified.reason}")

        tampered = bundle.model_dump(mode="json")
        tampered["event"]["metadata"]["observation"]["move"] = "Nc5"
        tamper_result = ets.verify_offline(tampered, policy=policy)
        if tamper_result.valid:
            raise RuntimeError("tampered Chess telemetry unexpectedly verified")

    print(f"ETS {version.version} / API {version.api_version}")
    print(f"game_id={game_id}")
    print(f"events_captured={len(MOVES)}")
    print("original_bundle=VALID")
    print("tampered_bundle=INVALID")


if __name__ == "__main__":
    main()
