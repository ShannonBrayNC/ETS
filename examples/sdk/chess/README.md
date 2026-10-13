# Chess evidence SDK walkthrough

This is the canonical SDK-4 end-to-end sample for ETS Dev.

It models four Chess Academy move observations. Each move records the move,
prior-state hash, resulting-state hash, and resulting FEN as evidence metadata.
The sample then downloads the final proof bundle, verifies it offline, changes
the recorded move, and confirms that the modified bundle no longer verifies.

Start ETS Dev:

```powershell
docker compose -f compose.sdk-dev.yml up --build
```

Run the walkthrough:

```powershell
python examples/sdk/chess/chess_evidence_walkthrough.py
```

Expected terminal result:

```text
events_captured=4
original_bundle=VALID
tampered_bundle=INVALID
```

This demonstrates integrity and reproducibility of submitted telemetry. It does
not prove that the physical or software chess move actually occurred outside
the observation process, nor that all expected observations were submitted.
