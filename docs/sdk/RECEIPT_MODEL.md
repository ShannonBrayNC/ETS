# ETS SDK receipt model

Contract: `ets.sdk.event_commit_receipt.v1`

A v1 event commit receipt contains:

- `event_id`
- `log_index`
- `event_hash`
- `tree_head`
- `inclusion_proof_url`
- `commitment_state = committed_local`

The receipt deliberately does not include `verified`, `true`, `complete`,
`authorized`, or `anchored` flags.

A developer may use the receipt to request proof material and then perform
independent verification. Synchronization, signed-checkpoint, anchoring, and
standing transitions require their own evidence/receipts and must not mutate the
meaning of this immutable local-commit receipt.
