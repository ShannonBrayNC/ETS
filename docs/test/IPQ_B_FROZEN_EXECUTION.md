# IPQ-B Frozen Edge Virtual Execution

Parent: #319  
Execution sprint: #351  
Frozen SUT: `75927c5a6c3f35e56c4f6e2cd88947e18a2ff333`

## Rule

The system under test is immutable. The qualification branch contains only post-baseline harness/evidence machinery. Every qualification job checks out the frozen SHA separately, asserts it exactly, and retains both SUT and harness identities.

## Native Edge evidence

The native group executes the frozen Edge suites for:

- software-held device identity and first-boot API-key provisioning;
- protected ingress boundaries;
- runtime proof-bundle verification facade;
- durable synchronization queue, recovery, idempotency and backpressure;
- RFC 5424 syslog parsing/capture diagnostics;
- upstream duplicate/conflict handling and raw-payload refusal;
- webhook exact-byte capture behavior.

A green native group qualifies only the behaviors directly asserted by those tests.

## Detached lifecycle probe

Because the frozen tree does not contain the previously anticipated end-to-end Edge Virtual restart integration tests, a detached probe composes only frozen public modules to reproduce the mandatory sequence:

1. first-boot local credential creation;
2. local durable queue capture while upstream is unavailable;
3. queue reconstruction after process restart;
4. reconnect to the frozen upstream acceptance boundary;
5. claim and drain the pending record;
6. mark the record synchronized;
7. replay the same idempotency key and require the upstream record count to remain one;
8. require the synchronization payload to contain no raw evidence bytes.

This is qualification machinery, not a product modification.

## Frozen credential-at-rest finding

The frozen `test_edge_device_identity.py` explicitly requires the reusable API key file contents to equal the API key itself, with filesystem mode `0600`. The detached probe reproduces the same condition. Therefore the credential-at-rest row is **FAIL / EXCLUDED from a hardened-secret claim** for the frozen baseline.

PR #334 later introduced encrypted/scrypt secret-at-rest hardening. It is post-baseline repair evidence only and must not be attributed to `75927c5...`.

## Identity claim boundary

Frozen identity metadata declares `key_custody=software_volume` and `hardware_attested=false`. Qualification may establish stable software-held identity across restart; it may not call that TPM/HSM custody or hardware attestation.

## Other nonclaims

IPQ-B does not establish universal source truth/completeness, physical device provenance, high availability, production GA, legal admissibility or compliance certification.
