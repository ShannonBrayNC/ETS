# Fictional Proof Bundle Template

Use this template to explain the ETS proof-bundle shape without committing generated hash material.

```json
{
  "schema_version": "ets.proof_bundle.v1",
  "event": "EvidenceEvent object",
  "event_hash": "sha256 hash of the canonical event payload",
  "leaf_hash": "sha256 hash of the event hash bytes",
  "tree_head": {
    "tree_size": 1,
    "root_hash": "Merkle root for the current tree",
    "created_at_utc": "2026-05-18T12:31:00Z",
    "log_id": "ets-local-dev",
    "signature_alg": null,
    "signature": null,
    "public_key_id": null
  },
  "inclusion_proof": {
    "schema_version": "ets.inclusion_proof.v1",
    "event_id": "evt_demo_001",
    "event_hash": "same event hash as above",
    "leaf_hash": "same leaf hash as above",
    "leaf_index": 0,
    "tree_size": 1,
    "root_hash": "same Merkle root as above",
    "audit_path": []
  },
  "verification_result": {
    "valid": true,
    "reason": "ok"
  }
}
```

Generate the real local bundle from the running API:

```powershell
Invoke-RestMethod http://localhost:8000/api/v1/bundles/evt_demo_001 `
  -Headers @{ "X-ETS-Tenant" = "tenant_demo"; "X-ETS-Workspace" = "workspace_alpha" } |
  ConvertTo-Json -Depth 100
```
