# ETS Python Application SDK

Contract: `ets.application.sdk.v1`

SDK-2 adds synchronous `ETSClient` and asynchronous `AsyncETSClient` remote
clients over the existing ETS v1 API.

## Supported operations

- service health and version;
- explicit API compatibility check;
- event capture;
- event lookup and bounded listing;
- inclusion proof retrieval;
- consistency proof retrieval;
- portable proof-bundle retrieval;
- strict offline verification using the existing verifier;
- strict online verification using the existing verifier transport and trust model.

The client performs no automatic retries. Evidence writes carry application
identity semantics, so callers must choose retry behavior deliberately rather
than allowing a transport library to repeat writes invisibly.

## HTTPS and development HTTP

HTTPS is the default requirement. Plain HTTP is accepted only for an explicitly
enabled loopback ETS Dev endpoint.

## Authentication

Use exactly one remote-authentication mode:

```python
ETSClient("https://ets.example", api_key="...")
```

or:

```python
ETSClient("https://ets.example", bearer_token="...")
```

Tenant/workspace headers are development-only. They can be configured with
local-header/local-API-key profiles, but cannot be configured together with a
bearer token.

## Receipt semantics

`capture()` returns `EventCommitReceiptV1`. The client converts the current
API append response into the frozen SDK receipt and assigns only
`commitment_state="committed_local"`.

That receipt is not a claim of verification, completeness, source truth,
authorization standing, synchronization, or external anchoring.

## Async

`AsyncETSClient` exposes the same remote operations. Online verification reuses
the hardened synchronous verifier in a worker thread so the event loop is not
blocked while preserving one verifier implementation and one trust model.


## Server authorization

Bearer identity and scope do not grant every operation. The issuer must assign a signed ETS role: `evidence_producer` permits capture/reconciliation, `viewer` permits reads, and `auditor` permits verification/export without creation. Missing roles or insufficient authority return HTTP 403 / `ETS_AUTH_FORBIDDEN`, mapped by the SDK to `authorization_failed`. Arbitrary client capability claims do not grant permissions. See the [core route matrix](../security/CORE_API_AUTHORIZATION.md) for aliases and migration from previously accepted roleless tokens.

## Signed offline round trip

Python 3.12+ is required. From an installed test-kit environment (or an editable
checkout), run:

```powershell
python examples/sdk/python/offline_roundtrip.py --output ./sdk-sample
```

The parent directory must exist; the output directory must be new. This example
uses real `ets.sdk` local helpers, an in-memory core log, a newly generated ephemeral
**sample** signer, and the existing strict CLI. It makes no network calls, saves no
private key and does not configure a real issuer. It writes `event.json`,
`bundle.json`, `sample-trust.json`, `tampered-bundle.json`, the synthetic artifact
and three fresh JSON reports. Expected summary:

```text
signed: valid
tampered: invalid
missing-trust: indeterminate
standing_status: checkpoint_only
private_key_saved: false
```

For reproducible test artifact bytes, add `--deterministic-smoke`; its fixed key is
PUBLIC TEST MATERIAL. Never use that option or trust file for customer evidence.
Report timestamps intentionally remain fresh. A second run requires a new output
directory; existing files are protected.

To exercise an existing complete frozen Windows verifier installation instead:

```powershell
python examples/sdk/python/offline_roundtrip.py --output ./frozen-sample `
  --verifier 'C:\reviewed-runtime\ets-verify.exe'
```

Keep the full frozen runtime directory together. This is a user-supplied executable
path, not a promise that the Store candidate exposes an execution alias.
The GUI requires its configured WebView2 runtime; this standalone CLI does not.

For Desktop, choose `bundle.json`, choose `sample-trust.json` separately, enter
expected log ID `ets-synthetic-sdk-example`, and verify. The test key is selected
only for this synthetic example. Test `tampered-bundle.json` as a failure and
missing trust as indeterminate; do not turn on unsigned acceptance.

## Read a saved event and capture it remotely

This is a real endpoint operation, unlike the local example. Replace the synthetic
scope/identity with a deliberately prepared event in your authorized **test**
workspace, and retain its exact ID/content before capture. Do not submit test data
to production merely because a token is available.

```python
import os
from pathlib import Path

from ets.core.models import EvidenceEvent
from ets.sdk import ETSClient

# The file must already contain the intended authorized scope and stable event ID.
event = EvidenceEvent.model_validate_json(Path("prepared-event.json").read_bytes())
with ETSClient(
    os.environ["ETS_TEST_BASE_URL"],  # HTTPS endpoint
    bearer_token=os.environ["ETS_TEST_BEARER_TOKEN"],
    timeout_seconds=10,
    max_response_bytes=4 * 1024 * 1024,
) as client:
    client.check_compatibility()
    receipt = client.capture(event, correlation_id="sdk-test-workflow-01")
    with Path("receipt.json").open("x", encoding="utf-8") as output:
        output.write(receipt.model_dump_json(indent=2))
    bundle = client.bundle(receipt.event_id)
    with Path("downloaded-bundle.json").open("x", encoding="utf-8") as output:
        output.write(bundle.model_dump_json(indent=2))
```

A failure after capture may leave an accepted event without a saved receipt. Follow
[reconciliation](TASK_GUIDE.md#retry-duplicate-detection-and-reconciliation), not a
blind rerun/new event ID. This snippet intentionally has no automatic retry.

## Verify independently in Python and through the CLI

```python
from pathlib import Path

from ets.core.bundle import EvidenceProofBundle
from ets.verifier.service import TreeHeadTrustStore, VerifierPolicy, verify_offline_bundle

bundle = EvidenceProofBundle.model_validate_json(Path("downloaded-bundle.json").read_bytes())
# Obtain this public material through your trusted, out-of-band channel.
trust = TreeHeadTrustStore.model_validate_json(Path("reviewed-trust.json").read_bytes())
outcome = verify_offline_bundle(
    bundle,
    trust_store=trust,
    policy=VerifierPolicy(expected_log_id="your-reviewed-log-id"),
)
if not outcome.valid or not outcome.signature_verified:
    raise RuntimeError("Verification failed; inspect sanitized checks")
assert outcome.standing_status == "checkpoint_only"
```

This in-process example assumes already-bounded trusted-size files. For untrusted
file ingestion use the strict CLI's bounded parsing, or apply equivalent limits
before loading. Library outcomes have `valid`/checks, not the CLI's `.status` field.
Generate a strict fresh report using the same exported bytes:

```powershell
& ./.venv/Scripts/python.exe -I -m ets.verifier.cli offline ./downloaded-bundle.json --trust-store ./reviewed-trust.json `
  --expected-log-id your-reviewed-log-id --report ./verification.json
```

Exit 0 means valid under the selected policy; 1 and 2 are failures with finer JSON
status/reason details. Export failure is separate from verification failure.
See the [full CLI contract](../../ets/verifier/README.md). Hash the actual retained
artifact separately against `content_hash`; bundle verification does not fetch it.

## Local helpers versus remote receipts

`create_evidence`, `hash_evidence`, `append_evidence`, `get_inclusion_proof`,
`verify_evidence` and `verify_inclusion_proof` are the public local facade.
`append_evidence(store, event)` returns a core `LogEntry`, not
`EventCommitReceiptV1`. Low-level hash/inclusion checks are not the full strict
signed-checkpoint trust policy. The offline sample deliberately uses core bundle,
signing and proof types for the missing local orchestration rather than inventing
an SDK `export_bundle()` method.

An in-memory store is not durable. Choosing `SQLiteEventStore` for your local
application requires its own lifecycle, backup, synchronization and concurrency
qualification; SDK examples do not turn it into a production service.

## Async and bounded pagination

`AsyncETSClient` exposes awaited remote operations; its `verify_offline` helper
is synchronous, while `verify_online` is awaited and reuses the strict verifier
in a worker thread. Do not `await client.verify_offline(...)`.

```python
import asyncio
import os
from ets.sdk import AsyncETSClient

async def inspect_test_scope():
    async with AsyncETSClient(
        os.environ["ETS_TEST_BASE_URL"],
        bearer_token=os.environ["ETS_TEST_BEARER_TOKEN"],
    ) as client:
        await client.check_compatibility()
        offset = 0
        # Explicitly bounded example, not an infinite stream or snapshot.
        for _ in range(10):
            page = await client.list_events(limit=100, offset=offset)
            for item in page.items:
                print(item.event.event_id, item.log_index)  # no body or secret logging
            if len(page.items) < 100:
                break
            offset += len(page.items)

asyncio.run(inspect_test_scope())
```

A moving log may need deduplication/checkpoint tracking and more than ten pages;
this sample does not prove complete source ingestion. Bound concurrent captures
with an application semaphore and preserve each event's uncertain state.
Cancellation cannot promise that a server write did not commit. Python clients
support injected `httpx` transports for tests; `verify_online` uses the verifier's
own HTTP path, so an SDK mock transport is not an online-verifier network mock.

## Errors, auth and deployment checklist

Catch `ETSApplicationError` and inspect `code`, `status_code`, `api_code` and
`correlation_id`; sanitize messages/details before logging. Use a separate outer
boundary for validation, filesystem and cancellation failures. Do not expose raw
customer payloads in logs. For async clients use `async with`; for sync clients
use `with` or close explicitly. Token acquisition/refresh, durable queues,
batching and rate limits are application responsibilities.

Read the [task guide](TASK_GUIDE.md), [industry cookbook](INDUSTRY_COOKBOOK.md),
[compatibility contract](COMPATIBILITY.md) and [test-kit checklist](TEST_KIT.md)
before widening from synthetic tests to a live deployment.
