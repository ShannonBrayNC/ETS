# Agent 365 telemetry semantics and custody profile

`Agent365TelemetryCustodyProfileV1` is the bounded OBS-03 contract for recording the exact
Microsoft OpenTelemetry Distro version, the observed semantic-schema version, privacy controls,
and two independently governed telemetry destinations.

The profile deliberately has no default package version or attribute names. A controlled-tenant
qualification must fill them from the pinned deployment and retained observations. The contract
keeps blueprint ID, instance application ID, object ID, and package ID separate. It also assigns
separate keys and values to case, mission, run, conversation, trace, and span identifiers; those
identifiers may be linked by retained evidence but cannot be substituted for one another.

## Delivery evidence

`Agent365DeliveryObservationV1` records three independent receipt pairs:

1. a Microsoft backend ingestion/query receipt;
2. an application exporter receipt;
3. an ETS evidence-custody record.

Each receipt requires a durable reference and SHA-256 commitment. Exporter success does not imply
Microsoft ingestion, and Microsoft ingestion does not imply ETS custody. The assessment reports
each proposition separately and marks delivery complete only when all three are present.

## Privacy and dual custody

The attribute allowlist must include the exact identity and correlation schema. Raw conversation,
prompt, tool-payload, token, and authorization-header content is prohibited. The profile requires
one Microsoft observability destination and one ETS evidence destination with distinct identities,
retention periods, encryption profiles, and access policies.

This contract does not prove that the allowlisted attributes are semantically correct, that all
events were ingested, that a tenant is qualified, or that an application action occurred.

## Reproducible checks

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_agent365_telemetry_custody.py
.\.venv\Scripts\python.exe -m ruff check ets/demos/agent365_telemetry_custody.py tests/test_agent365_telemetry_custody.py
.\.venv\Scripts\python.exe -m mypy ets/demos/agent365_telemetry_custody.py
```

Live OBS-03 qualification remains open until a retained controlled-tenant profile supplies the
actual pins, positive delivery receipts, privacy-negative evidence, and reviewer acceptance.
