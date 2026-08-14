# ETS Connector Package Manifest v1

Status: G2H-D candidate  
Parent: #256  
Sprint: #302

## Purpose

Define the static integrity, provenance, compatibility, and qualification boundary for connector
packages that are not compiled into the trusted ETS distribution.

Package verification happens **before** activation and deliberately does not import or execute
third-party Python code.

## Manifest contract

A package root contains `connector-package.json` using schema
`ets.connector.package.v1`. The manifest declares:

- package ID and version;
- connector ID;
- publisher identity, publisher class, and qualification state;
- repository/source provenance;
- supported connector SDK, Gateway host, and capture-envelope versions;
- connector definition and settings-schema paths;
- adapter and conformance entry points using `module.path:attribute` syntax;
- a sorted, complete file inventory with SHA-256 for every package file except the manifest itself;
- an aggregate SHA-256 over the canonical file-integrity inventory.

Unknown fields fail closed.

## Exact package contents

The verifier walks the package directory without following symlinks. Every regular file other than
`connector-package.json` must appear exactly once in the manifest and no undeclared file may be
present. Symlinks and special files are rejected.

The connector definition, settings schema, adapter module, and conformance module must all be
covered by the integrity set.

Aggregate integrity is the SHA-256 of canonical JSON containing the sorted `path`/`sha256` pairs.
This aggregate identifies one static package content set; it is not an ETS evidence proof.

## Compatibility

Before activation can be considered, package declarations must match the local:

- `ets.connector.sdk.v1` contract;
- `ets.gateway.connector-host.v1` host contract;
- `ets.capture.v1` envelope contract.

The packaged connector definition must declare the same connector ID and SDK contract as the
package manifest.

Compatibility failure is distinct from integrity failure.

## Publisher and qualification classes

The v1 vocabulary distinguishes:

- `lantern_builtin`;
- `lantern_qualified_third_party`;
- `community_unqualified`.

Qualification state is separately represented as `qualified`, `unqualified`, or `revoked`.
Community packages cannot self-declare `qualified`.

`ConnectorPackageActivationPolicy` is intentionally separate from integrity verification. The
default policy permits only `lantern_qualified_third_party` packages in `qualified` state. A local
development host may explicitly adopt a different policy, but package integrity alone never grants
activation.

## Provenance

The manifest records a repository URL, source revision, and optional build reference. These fields
preserve package-source provenance for operators and review systems. They do not establish that the
publisher, repository, or source revision is trustworthy.

## Entry points

Adapter and conformance entry points are validated syntactically and their module files must be
covered by the package integrity inventory. Static verification does not import them.

A later loader may import only after:

1. static integrity verification succeeds;
2. compatibility succeeds;
3. activation policy authorizes the publisher/qualification state;
4. the package-specific conformance gate succeeds in an approved execution boundary.

## Reference sample

`examples/connectors/sample_third_party` is intentionally a `community_unqualified` package. It
exists to demonstrate packaging and static verification. The default activation policy rejects it.
The placeholder adapter/conformance modules are never imported by the static verifier.

## Developer workflow

1. Build a connector against the published G2A SDK contract.
2. Keep reusable source credentials outside package settings; use opaque G2B references.
3. Create strict connector definition and settings schema files.
4. Declare adapter and conformance entry points.
5. Produce a sorted complete package file list and SHA-256 for each file.
6. Compute the aggregate package-content SHA-256 from that canonical list.
7. Record repository/source provenance and supported host/SDK/capture versions.
8. Run static package verification.
9. Run connector conformance in the approved isolated execution boundary.
10. Publish qualification state separately from evidence collected by the connector.

## Nonclaims

Package integrity means only that files match a declared static digest inventory. Connector
conformance means only that a package satisfies the declared SDK/behavioral qualification tests.
Neither property verifies the truth, completeness, legal admissibility, or compliance status of
evidence collected through that connector.
