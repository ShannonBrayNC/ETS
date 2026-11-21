# Scheduled DSC 3 read/test runner profile v1

Status: DSC-01 implementation-contract milestone; live qualification remains open.

`ets.connectors.enterprise.dsc3_read_test` defines a strict, machine-validated contract for one
read-only standalone DSC 3 `config test` worker. The profile records:

- the scheduler name and execution identity;
- interval, timeout, non-overlap, reboot and freshness behavior;
- the OS and architecture;
- digest-pinned DSC executable, resources, adapters, schemas and dependencies; and
- the reviewed desired-configuration digest.

The only accepted execution mode is `standalone_dsc3`, the only operation is `config_test`, and the
profile requires `resident_lcm_present=false`. This prevents the contract from implying that DSC 3
provides a resident Local Configuration Manager or that a Machine Configuration assignment was
evaluated. Production profiles reject resources marked `proof_of_concept` and reject
`Microsoft.Windows/Registry` by name even if it is mislabeled; Microsoft documents that bundled
resource as a proof of concept that must not be used in production.

## Fail-closed evaluation

`assess_dsc3_read_test` evaluates process exit and the normalized structured resource results as
separate evidence. A zero process exit without structured output is `unknown`; a nonzero process
exit is `unknown` even if partial structured output reports drift. Only a fresh, successful process
with internally consistent structured results can produce `compliant` or `drift`.
Each observation is bound to the profile ID and reviewed desired-configuration digest, and its
resource set must exactly match the pinned profile; a mismatch is `unknown`.

When no invocation is available, a retained prior success produces `missed_or_dead_checker`. When
the latest completed invocation exceeds the profile's freshness threshold it produces
`stale_checker`. Both are `unknown`, not compliant. The assessment retains the prior success time
or observation age so downstream evidence can state why the checker is unknown.

## Reproduction

From the repository root with the development environment installed:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_dsc3_read_test.py
.\.venv\Scripts\python.exe -m ruff check ets/connectors/enterprise/dsc3_read_test.py tests/test_dsc3_read_test.py
.\.venv\Scripts\python.exe -m mypy ets/connectors/enterprise/dsc3_read_test.py
```

Passing these tests establishes only the local contract and evaluator behavior. DSC-01 remains open
until a named scheduler and identity run the digest-pinned profile repeatedly on the selected host,
retain deliberate drift and stable-repeat observations, demonstrate revoked/missed collection as
unknown, and preserve the resulting evidence and limitations for independent review.

Platform reference: [Microsoft.Windows/Registry](https://learn.microsoft.com/en-us/powershell/dsc/reference/resources/microsoft/windows/registry/?view=dsc-3.0).
