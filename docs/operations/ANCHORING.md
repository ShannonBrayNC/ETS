# External Trust Anchoring

ETS Sprint 6 adds deterministic root exports that can be copied to external
systems. This is an operational checkpoint mechanism, not a consensus protocol
and not a proof that the external service behaved correctly.

## Anchor Export

`GET /anchors/latest` exports:

- latest ETS checkpoint hash
- current Merkle root
- signed tree head envelope
- export timestamp
- deterministic anchor hash
- target profile

Supported target profiles are:

- `github_release`
- `azure_immutable_storage`
- `local_file`

The target value records intended publication context. The API does not upload
to GitHub or Azure; deployment automation should publish the returned JSON and
retain the external URL, release ID, blob version, or retention-policy metadata.

## GitHub Release Artifact Profile

For release anchoring:

1. Fetch `GET /anchors/latest?target=github_release`.
2. Store the JSON as a release asset, for example
   `ets-anchor-20260526T150000Z.json`.
3. Record the release URL in deployment evidence.
4. Later, download the JSON and submit it unchanged to `POST /verify/anchor`.

This demonstrates that the anchor document is internally consistent and can be
compared with a later ETS tree head. It does not prove GitHub availability,
GitHub identity, or release immutability without separate repository controls.

## Azure Immutable Storage Profile

For Azure immutable blob storage:

1. Fetch `GET /anchors/latest?target=azure_immutable_storage`.
2. Upload the JSON to a container with immutable retention or legal hold
   configured.
3. Preserve the blob URL, version ID, retention policy, and uploader identity in
   deployment records.
4. Later, download the JSON and submit it unchanged to `POST /verify/anchor`.

ETS does not configure storage policies. Operators must validate retention,
access control, lifecycle policy, and deletion protection separately.

## Verification

`POST /verify/anchor` checks the exported object without hidden server state:

- Merkle root matches the signed tree head root.
- Tree size matches the signed tree head size.
- Source log ID matches the signed tree head log ID.
- Anchor hash matches the canonical export payload.
- Anchor ID matches the deterministic anchor hash prefix.

If the signed tree head includes Ed25519 fields, verify the tree-head signature
with `POST /verify/signature` and a trusted public key. Anchor verification does
not by itself establish key custody or signer identity.

## Replay And Corruption Checks

After backup restore, migration, or incident response:

1. Fetch a current `GET /api/v1/log/head`.
2. Verify a sample of inclusion proofs for known event IDs.
3. Re-import the latest external anchor with `POST /verify/anchor`.
4. Compare the restored tree head with the anchored tree head.
5. Request a consistency proof from the anchored tree size to the current tree
   size when the restored log has advanced.

Rollback, fork, or omission concerns should be handled as incidents. Preserve
the restored database, exported anchors, relevant tree heads, and API audit logs
for review.

## Demo

```powershell
npm run demo:anchor
```

The demo appends synthetic non-PII events, exports a GitHub release-profile
anchor, verifies the exported JSON, then demonstrates deterministic failure for
a tampered Merkle root.

## Limitations

- Local unsigned tree heads are not production trust anchors.
- ETS does not prove Byzantine consensus, Internet-scale liveness, or external
  service immutability.
- GitHub and Azure publication are deployment automation responsibilities.
- Anchor timestamps are evidence metadata, not independently trusted time
  unless the external system supplies a trusted timestamping control.
