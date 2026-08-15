# IPQ-C Frozen Gateway Native-Ingress Result

Parent: #320  
Execution sprint: #352  
Qualification run: `31860502073`  
Frozen SUT: `75927c5a6c3f35e56c4f6e2cd88947e18a2ff333`

## Disposition

**PASS — controlled frozen Gateway native-ingress qualification.**

The detached qualification harness checked out and asserted the immutable frozen SUT SHA before executing each independent ingress family. All four families completed with pytest exit `0`. These results qualify only the behaviors directly exercised by the retained tests and artifacts.

| Family | Result | Tests | Artifact ID | Artifact ZIP SHA-256 |
| --- | --- | ---: | ---: | --- |
| HTTPS | PASS | 41 | `9240413827` | `a3993c53d356b90fc38d35aaa80395553a7c2091e9bd2462106b3d1653ba6d54` |
| RFC 5425 Syslog/TLS | PASS | 44 | `9240410479` | `77973c2a777d65605f8b68f4ce39af43ca4769fe1d1cc1ee99a0357553c56031` |
| File/Drop | PASS | 67 | `9240412414` | `e506acc1794f48d4b898c16ad69ed404a9c95985544f850cda904c371f6fe648` |
| OTLP HTTP/gRPC | PASS | 57 | `9240411506` | `6cf06a233ba31d02f9784a1229ef13bb9e3dc487bfdd34ea6b55ab1afb6572b1` |
| **Total** | **PASS** | **209** |  |  |

## Qualified boundary

### HTTPS

The retained frozen suite reproduces HTTP/HTTPS capture, ingress representation, host lifecycle and shutdown behavior within the selected test boundary. PASS does not imply that an upstream source is truthful or complete.

### RFC 5425 Syslog/TLS

The retained frozen suite reproduces the selected TLS profile, RFC 5425 framing, ingress/host, negative/limit and shutdown/drain behaviors. PASS applies to the controlled test paths only and is not a claim about arbitrary external network availability.

### File/Drop

The retained frozen suite reproduces the selected filesystem-object digest/capture and file-drop ingress/host behaviors. Qualification is limited to the traversal, object, digest and host semantics actually asserted by the selected tests.

### OTLP HTTP/gRPC

The retained frozen suite reproduces the selected OTLP logs/metrics/traces capture, protobuf representation, partial-commit behavior, HTTP, gRPC and gRPC-mTLS paths. PASS does not convert telemetry producer assertions into source truth.

## Evidence integrity

For every family the workflow retained:

- exact frozen `sut_sha` identity;
- qualification `harness_sha` identity;
- pytest log;
- JUnit XML;
- group manifest;
- uploaded artifact ZIP with GitHub-reported SHA-256 digest.

The harness is post-baseline qualification machinery; the system under test is always the immutable frozen SHA above.

## Explicit exclusions

This result does **not** establish or claim:

- source truth or source completeness;
- high availability or production GA readiness;
- availability of arbitrary external networks or producers;
- legal admissibility or compliance certification;
- hardware identity or hardware attestation;
- behavior introduced after the frozen baseline;
- equivalence between software-observed ingress and independently verified real-world events.

## Finalization rule

This result may be merged as retained qualification evidence only after the qualification branch is synchronized to then-current `main`, exact-head repository gates are green, and a fresh independent LanternProtocol review approves that synchronized head. Synchronization must not modify the frozen SUT SHA or reinterpret these retained results.
