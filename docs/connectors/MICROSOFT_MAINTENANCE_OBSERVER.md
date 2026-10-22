# Synthetic SharePoint maintenance-item observer

Status: DD-020 development candidate; simulated source, unqualified.
Owner: ETS. Controlling issue: https://github.com/Lantern-Protocol/demodriver/issues/3

`ets.connectors.enterprise.microsoft_maintenance_observer` compares already-retained
synthetic Graph item bytes against a verifier-owned `MaintenanceExpectation`.
It reuses `snapshot_sharepoint_metadata_record` for a bounded metadata commitment.
The input is limited to 16 KiB; no network request or state advance occurs.

The proposed maintenance fixture field mapping is `CaseId`, `TicketId`,
`ApprovalStatus`, `DraftSha256`, and `OutboundCommunicationAllowed`, under the
Graph item `fields` object. These are fixture column names, not built-in Microsoft
columns or an assertion that a tenant/list has been provisioned. Expected approval
is `approved` and outbound communication is strictly JSON `false`.

The comparison records raw-source and expectation SHA-256 commitments, bounded
assertion names/results, a minimized metadata commitment when the source is complete,
and optional producer success context. It never exports source field values or unknown
fields. The caller must retain the exact synthetic input bytes before interpretation.
No credential or real customer input is authorized by this profile.

Results are `observed` for all matching fields; `unresolved` for missing, malformed,
duplicate-key, non-finite, non-UTF-8 or wrong-type source; `contradictory` for a
complete source that differs from the expected state or is deleted. A producer success
claim cannot override any result. Oversized input and malformed expectations raise
bounded `ValueError`s before interpretation. Restoring the complete original input
recovers to `observed` without changing the expected state.

This module does not authenticate Graph acquisition, collector identity, tenant/site/list,
ETag freshness, or the human who approved a response. It does not establish approval
scope/expiry: those remain QRF's responsibility. It does not seal an ETS event or verify
a signature. A digest does not establish truth, completeness or authority.

The Ranger mission parser and frozen mission contract are unchanged. Agent365 package
inventory is a separate source class. Later integration must use authorized read-only
acquisition, source envelopes, exact target identity and freshness, QRF approval binding,
and portable proof verification before any live qualification claim.

Validation:

```bash
python -m pytest -q tests/test_microsoft_maintenance_observer.py tests/test_microsoft_sharepoint_state.py
ruff check ets/connectors/enterprise/microsoft_maintenance_observer.py tests/test_microsoft_maintenance_observer.py
mypy --follow-imports=silent --strict ets/connectors/enterprise/microsoft_maintenance_observer.py
```

Fault/recovery tests remove each required field despite producer success, substitute
each contrary target value, reject wrong boolean types and deleted targets, then restore
the valid synthetic item. They also prove unknown sensitive strings do not enter receipts.
