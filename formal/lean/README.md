# Lean proof toolchain

`lean-toolchain` pins `leanprover/lean4:v4.35.0`, the compiler version used by the
recent passing engineering proof runs. Update this file deliberately and run all
proofs before accepting a compiler upgrade. Elan selects it when commands execute
from this directory, including `scripts/run-lean-proofs.sh`.

CI installs elan without a default compiler, explicitly installs the pinned
compiler, and records `lean --version` in `artifacts/lean-proofs/toolchain.txt`.
Setup/download commands get at most three attempts, each bounded to 180 seconds,
with five seconds between attempts and a ten-second forced-termination grace.
The bootstrap script download also has connection/transfer and retry limits.
Exhausted setup failures remain failures; they never produce a proof success.

Proof execution itself is not retried, bypassed or weakened. Existing per-proof
logs, exit codes and the overall 30-minute job timeout remain. A download failure
or setup timeout means proofs did not execute, not that a theorem failed.

The retry helper has local behavioral tests:

```bash
python3 -m unittest discover -s tests/ci -p test_ci_retry.py
bash scripts/run-lean-proofs.sh
```

The first command tests transient recovery, permanent failure, timeout and argument
validation without network access. The second requires the pinned Lean toolchain
and executes the actual proofs. Retry tests alone do not validate theorems.

References: [Elan toolchains](https://lean-lang.org/doc/reference/latest/Build-Tools-and-Distribution/Managing-Toolchains-with-Elan/)
and [elan installer options](https://github.com/leanprover/elan/blob/master/elan-init.sh).
