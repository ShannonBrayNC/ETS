# IPQ-E Frozen Enterprise Execution

Parent: #322  
Execution sprint: #345  
Frozen SUT: `75927c5a6c3f35e56c4f6e2cd88947e18a2ff333`

## Rule

The IPQ-E system under test is immutable. Qualification tooling executes from a later harness revision and checks out the frozen SUT into an isolated `sut/` directory. No later connector, Gateway, Console, schema, or test code may be copied into the frozen tree and represented as baseline behavior.

Every evidence artifact records both the frozen `sut_sha` and the executing `harness_sha`.

## Baseline-native evidence groups

### GitHub Audit

- `tests/test_github_audit_connector.py`
- `tests/integration/test_gateway_github_connector.py`

The baseline integration path checks authoritative server tenant/workspace scope, minimized evidence representation, local append plus durable sync enqueue before checkpoint release, pre-commit backpressure, and append-before-enqueue retry recovery.

### AWS CloudTrail

- `tests/test_aws_cloudtrail_connector.py`
- `tests/integration/test_gateway_aws_connector.py`

The baseline integration path checks the same shared Gateway commitment invariants while retaining the CloudTrail-specific bounded management-event representation and opaque NextToken checkpoint behavior.

### Okta System Log

- `tests/test_okta_system_log_connector.py`
- `tests/integration/test_gateway_okta_connector.py`

The baseline integration path checks server-authoritative scope, minimized System Log metadata, server-generated next-link checkpoint release, backpressure, and partial-commit retry recovery. Adapter tests provide the source authentication/authorization/throttle/retry, next-link validation, and retention-gap behavior available in the frozen product.

### Generic REST

- `tests/test_generic_rest_transport.py`
- `tests/test_generic_rest_extraction.py`
- `tests/integration/test_gateway_generic_rest_connector.py`

The frozen tests cover exact HTTPS trusted-host policy, sensitive static header/query rejection, response-size and timeout bounds, redirect/auth/authorization/throttle/retry classification, declarative allow-listed extraction, source cursor resume, overlapping time-window resume without completeness claims, payload-scope rejection, checkpoint release, pre-commit backpressure, conflicting retry, and append-before-enqueue recovery.

## Collector semantics

Each matrix group executes separately. Pytest exit codes are interpreted as follows:

- `0` → frozen product group `PASS`;
- `1` → frozen product group `FAIL`, retained as evidence while the collector job completes;
- any other pytest exit → harness/collection error, which fails the workflow and must be corrected before the product result can be trusted.

This prevents a genuine baseline test failure from being hidden while also preventing a broken harness from being mislabeled as a product failure.

## Result completion

After the detached run, `IPQ_E_FROZEN_RESULT.md` must map the mandatory #322 scenarios to PASS/FAIL/BLOCKED/EXCLUDED with exact run/job/artifact references. Passing implementation or source review alone is not sufficient for a PASS row.

If a mandatory behavior is not exercised by the selected baseline-native tests, add a detached controlled fixture or explicitly classify the row as non-pass. Do not infer coverage from a class/function existing in source.

## Security and claim boundary

Fixtures use synthetic credential/marker literals only. The qualification artifacts must not contain real reusable credentials or real raw source payloads.

A PASS means the controlled behavior was reproduced on the exact frozen SUT. It does not establish source truth, source completeness, continuous external-service availability, production credential readiness, legal admissibility, compliance, production GA, or later connector capabilities.
