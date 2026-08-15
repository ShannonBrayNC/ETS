# IPQ-C Frozen Gateway Native-Ingress Execution

Parent: #320  
Execution sprint: #352  
Frozen SUT: `75927c5a6c3f35e56c4f6e2cd88947e18a2ff333`

## Rule

The frozen SUT is immutable. The detached harness checks out exact `75927c5...` into `sut/`, executes only baseline-native product/tests from that tree, and records both `sut_sha` and `harness_sha`. Later Gateway changes cannot be substituted for a missing frozen behavior.

## Independent evidence families

### HTTPS

The HTTPS group covers the frozen HTTP capture/host/representation boundary plus the HTTPS host integration path. Final row mapping must distinguish authorized server scope, ingress bounds, conflicts/backpressure and shutdown behavior according to the assertions actually executed.

### RFC 5425 Syslog/TLS

The Syslog group covers frozen TLS profile, framing, host and ingress behavior plus host, limits, negative and shutdown/drain integration tests. PASS means only the controlled RFC 5425/mTLS behaviors reproduced by those tests.

### File/Drop

The File/Drop group covers streamed object digest/capture, frozen file ingress and host behavior. Final qualification must explicitly map traversal, symlink, race and exact-bound negatives only where the selected tests directly exercise them.

### OTLP

The OTLP group covers frozen logs/metrics/traces capture and protobuf representation, partial-commit handling, HTTP, gRPC and gRPC-mTLS paths. HTTP/gRPC representation equivalence and partial-success semantics must be scored from direct assertions rather than implementation presence.

## Collector semantics

Each family runs independently. Pytest exit `0` is retained as group PASS, exit `1` as frozen-product group FAIL while the collector completes, and collection/internal/no-test errors fail the harness. A green group is candidate evidence; `IPQ_C_FROZEN_RESULT.md` maps the individual #320 mandatory scenarios conservatively after the first run.

## Claim boundary

This qualification proves only controlled native-ingress behavior reproduced on the immutable frozen SHA. It does not establish source truth/completeness, external-network availability, high availability, legal admissibility, compliance certification, hardware attestation or production GA.
