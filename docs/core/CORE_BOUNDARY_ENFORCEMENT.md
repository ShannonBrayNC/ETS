# ETS Core Boundary Enforcement

Status: C1.4 implementation contract

## Purpose

C1.4 makes the normative ETS Core boundary executable. The boundary is defined by `docs/core/core_boundary_manifest.json`, validated by `tools/check_core_boundaries.py`, and exercised by `tests/unit/test_core_boundaries.py` on every normal CI run.

## Normative module set

Only modules explicitly listed in the boundary manifest are treated as the C1 normative dependency graph. This avoids accidentally granting stable-core status to legacy reference storage, reporting, federation, anchoring, or hosted-product modules that still reside under the broader repository namespace.

Adding a normative module requires all of the following in one reviewed change:

1. update the boundary manifest;
2. pass forbidden-import and cycle validation;
3. update the public API manifest when exports change;
4. document the protocol and compatibility impact; and
5. obtain independent review.

## Enforced rules

The validator fails when:

- a declared normative module is absent;
- a normative module imports a prohibited product, network, cloud, storage, hosting, or reporting dependency;
- the normative dependency graph contains a cycle; or
- `ets.core.api.__all__` differs from the frozen public API list.

The runtime probe fails when importing `ets.core.api`:

- opens a network socket;
- connects to SQLite;
- reads configuration through `os.getenv`;
- configures global logging;
- starts a thread;
- loads prohibited product dependencies; or
- writes files into its clean working directory.

Repeated import must preserve the module identity and public export list.

## Commands

```bash
python tools/check_core_boundaries.py
python tools/check_core_boundaries.py --write-graph docs/core/CORE_DEPENDENCY_GRAPH.md
pytest tests/unit/test_core_boundaries.py
```

## Security boundary

These controls prove architectural isolation and the absence of the specifically instrumented import-time side effects. They do not prove evidence truth, host integrity, or the impossibility of every future Python side effect.

## Change control

Changes to normative modules, forbidden dependency prefixes, public symbols, dependency direction, probe coverage, or waivers require protocol-impact review and independent approval.
