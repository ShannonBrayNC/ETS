# ETS Core Normative Dependency Graph

Generated from `docs/core/core_boundary_manifest.json` by `tools/check_core_boundaries.py`.

```text
ets.core.api -> ets.core.canonical_json, ets.core.models, ets.core.profiles, ets.core.results
ets.core.canonical_json -> (none)
ets.core.errors -> (none)
ets.core.models -> ets.core.canonical_json
ets.core.profiles -> ets.core.errors
ets.core.results -> (none)
```

The graph is acyclic. Product hosting, storage, cloud, Edge, portal, reporting, and network modules are outside the normative boundary.
