# ADR-008: ETS Gateway Separates Source Identity, Hardware Signer Assurance, and Time Assurance

Status: Proposed for independent approval
Date: 2026-08-13
Parent: #215
Related: #221

## Context

Evidence provenance can be overstated if network location, TLS identity, payload identity, TPM presence or synchronized time are treated as universal proof. These signals establish different properties and must remain independently represented.

## Decision

### Source identity

1. Source IP/VLAN/location is contextual evidence, not sufficient identity.
2. Authenticated transport identity and payload-declared identity are preserved separately.
3. For syslog-TLS, certificate/transport sender identity is not automatically equated to syslog HOSTNAME.
4. Tenant/workspace authorization is resolved server-side from approved source/credential mapping.

### Device/signer

5. Software signer is development/lab only and visibly non-production.
6. Physical pilot reference requires TPM 2.0 or an approved conformance-equivalent hardware signer.
7. Production application code never receives exportable evidence-signing private-key bytes.
8. Device identity, transport identity and evidence-signing keys should be purpose-separated.
9. Rotation/revocation changes current trust/authorization state without rewriting historical evidence; historical signatures remain evaluated under applicable policy/key history.
10. Hardware attestation proves only declared measurements/claims checked by a verifier policy, not the absence of every runtime compromise.

### Time

11. Source observation time and Gateway receipt time are separate.
12. Local sequence/duration logic uses monotonic time where wall-clock movement could cause ambiguity.
13. NTPv4 is supported; NTS is preferred where enterprise infrastructure supports it.
14. Clock quality/rollback is explicit.
15. Authenticated time transport does not by itself prove that the time server's UTC value is correct.

## Consequences

- Verification can describe multidimensional provenance assurance rather than a single trust score.
- Legacy/weakly authenticated sources remain usable but transparently lower-assurance.
- Clock failures degrade time assurance without corrupting append order.
- TPM integration improves key custody without creating an unsupported statement that the entire appliance is trustworthy.

## Validation

G0 machine profile encodes these boundaries. G1/G3 tests validate source identity separation, time rollback behavior, signer unavailability, key non-exportability and hardware-backed signing on the reference appliance.
