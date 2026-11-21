# Microsoft365DSC read profile v1

Status: M365-01 contract milestone; live tenant and resource qualification remain open.

`ets.microsoft.m365dsc.read.v1` defines one bounded, read-only Microsoft365DSC resource and
property. A profile pins the operating system, exact PowerShell runtime, Microsoft365DSC module,
dependencies, supported resource, workload, target property, tenant and desired-property digest.
The current contract requires PowerShell 7.6.0 or newer. A Windows PowerShell LCM compatibility
path must be declared explicitly and must identify the installed PowerShell 7 executable; it does
not turn an older LCM runtime into the owning profile.

## Authority boundary

The collector is authorized only for the resource's `Get` and `Test` operations. The profile
rejects declared write grants and permission names that are visibly write-capable. This validation
is defense in depth, not a substitute for tenant-side consent review and negative authorization
tests.

An independently identified workload-native reader must observe the same property. Its identity,
API/module version, endpoint family and read permissions are pinned separately from the
Microsoft365DSC collector. The reader cannot be the collector identity. A supported resource and a
successful DSC `Test` result are not enough to report compliance without this native read-back.

## Assessment semantics

The assessment reports:

- `compliant` only when a fresh Microsoft365DSC `Test` and the native property digest both match
  the reviewed desired-property digest;
- `drift` only when `Test` reports drift and the native property digest also differs; and
- `unknown` for revoked collection authority, unsupported resources, runtime failure, missing
  native read-back, stale evidence, profile/target/identity mismatch, or disagreement between DSC
  and the independent reader.

Previously qualified profiles are retained as immutable digest records with `status=frozen`.
Selecting a new module or resource version creates a new profile; it does not silently rewrite the
standing of older evidence.

## Claim boundary

This milestone supplies deterministic validation and positive/negative fixtures. It does not prove
that the example resource is supported in a particular tenant, that listed permissions are
sufficient or least-privileged in Microsoft Entra, that consent has been revoked successfully, or
that a native workload command returned truthful live state. M365-01 remains open until reviewed
commands, tenant-side authority evidence, repeated live observations and retained native read-back
qualify the selected slice.
