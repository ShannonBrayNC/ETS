# Configuration assurance identity profile v1

Status: ID-01 contract milestone; live qualification remains open.

This profile turns the six identities required by the Microsoft configuration-assurance pilot into
a strict, machine-validated matrix. It records the tenant, principal/object ID, application ID,
Agent 365 blueprint or an explicit not-applicable reason, token audiences, roles, scopes, resource
allowlist, consent mode, cloud, licensing, feature maturity, access mode and qualification status
for the investigator, context reader, autonomous read broker, executor, verifier and exporter.

`ConfigurationAssuranceIdentityMatrixV1` in
`ets.connectors.enterprise.configuration_assurance_identity` fails closed when:

- any of the six roles is missing or duplicated;
- a read role claims write authority;
- the executor reuses the principal or application identity of the investigator, context reader or
  autonomous read broker;
- Enterprise MCP is represented as app-only instead of delegated interactive access;
- the autonomous read broker lacks its own non-interactive identity and explicit
  `platform_managed` or `byo_preview` registration mode; or
- an identity is marked `qualified` without retained evidence references.

The model deliberately accepts `unqualified` profiles so operators can review the intended access
shape before consent or deployment. Validation proves only that the matrix is internally
consistent. It does not prove that Microsoft issued a token, that the declared roles match live
assignments, that an allowlist is enforced, or that a principal can or cannot write. Those claims
require protected live positive and negative evidence under [ID-01](https://github.com/ShannonBrayNC/ETS/issues/960).

Enterprise MCP delegated interactive access and an autonomous application/workload broker are
separate authorization paths. A BYO broker registration remains explicitly preview-scoped and must
be qualified independently. The investigator receives no executor credential or approval-edit
authority through this contract.
