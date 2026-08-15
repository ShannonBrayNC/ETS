# IPQ-F Frozen Package and Microsoft Execution

Parent: #323  
Execution sprint: #347  
Frozen SUT: `75927c5a6c3f35e56c4f6e2cd88947e18a2ff333`

## Rule

The IPQ-F system under test is immutable. The qualification harness checks out the exact frozen SHA into `sut/`, records `sut_sha` and `harness_sha`, and executes the product/tests from the frozen repository root. Later Microsoft/Gateway changes are not copied into the SUT and cannot retroactively change its qualification result.

## Evidence groups

### Third-party connector package

Frozen `tests/test_connector_packages.py` covers the strict `ets.connector.package.v1` model, package/file digests, one-file tampering, undeclared files, symlinks, traversal/unknown fields, integrity-covered entrypoint modules, SDK/Gateway/capture compatibility, activation policy and deterministic aggregate digest behavior. Verification is static and does not import or execute connector package code.

The detached harness adds two negative cases against the frozen verifier without modifying it:

- remove declared `sample_connector.py` and require an exact-inventory integrity failure;
- replace declared `sample_connector.py` with a FIFO and require the frozen special-file rejection.

It also directly validates the three publisher classes (`lantern_builtin`, `lantern_qualified_third_party`, `community_unqualified`) and confirms a community package cannot self-assert a qualified state.

Package integrity/provenance is not ETS evidence verification and does not prove that events later emitted by package code are truthful or valid evidence.

### Microsoft common readiness

Frozen `tests/test_microsoft_connector_common.py` covers qualified cloud endpoint maps, customer endpoint-override rejection, canonical tenant/application identities, consent states, credential metadata states, provider-not-found/operational failures, and sanitization of credential references/provider details.

### Graph notification/subscription source boundary

Frozen:

- `tests/test_microsoft_graph_notifications.py`
- `tests/test_microsoft_graph_subscriptions.py`

These cover validation tokens, bounded resource/lifecycle parsing, unknown subscription/foreign tenant/clientState rejection, deterministic source-record identity, possible-gap lifecycle state, malformed/oversize rejection, create/renew/reauthorize/delete lifecycle, qualified national-cloud roots, auth/authorization/throttle classification, and in-memory token zeroization on client close.

This is explicitly a **source-side boundary**. The frozen baseline does not gain an end-to-end Gateway commitment claim from these tests, and this qualification does not close #305.

### Entra users/groups delta boundary

Frozen:

- `tests/test_microsoft_entra_connector.py`
- `tests/test_microsoft_entra_delta.py`
- `tests/test_microsoft_entra_delta_http.py`
- `tests/test_microsoft_entra_resync.py`

These qualify the frozen users/groups delta behavior including nextLink/deltaLink preservation, minimized identity/group metadata, changed/deleted removal markers, repeated entity observations, retry identity, same-cloud/same-collection cursor validation, bounded source-state links, HTTP/source error handling, and resync/gap behavior represented by the frozen implementation.

## Collector semantics

Each group executes independently. Pytest exits are interpreted as:

- `0` → group PASS;
- `1` → group FAIL retained as frozen-product evidence while the collector completes;
- any other exit → harness/collection error that fails qualification.

Detached package probes are qualification-harness assertions: if they cannot exercise the intended missing/special-file rejection or publisher distinction, the harness fails rather than relabeling the product result.

## Result completion

After the first detached run, `IPQ_F_FROZEN_RESULT.md` must map every mandatory #323 row to PASS/FAIL/BLOCKED/EXCLUDED and retain exact run/job/artifact identifiers and artifact SHA-256 digests.

Implementation presence alone is never a PASS. Live Microsoft production connectivity, real tenant consent, production credentials and full Graph Gateway commitment are outside this frozen controlled-fixture qualification unless separately evidenced.

## Claim boundary

A PASS proves only the bounded behavior reproduced on the exact frozen SUT. It does not establish source truth/completeness, legal admissibility, regulatory compliance, production GA, hardware attestation, live Microsoft service availability, or end-to-end evidence verification for an accepted notification/package.
