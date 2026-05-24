# ETS Release Checklist

Before any release:

- [ ] Version updated in `pyproject.toml`.
- [ ] `CHANGELOG.md` updated.
- [ ] `ruff check .` passes.
- [ ] `mypy` passes.
- [ ] `pytest` passes.
- [ ] Explorer UI build passes when present.
- [ ] CI workflow is green.
- [ ] Security docs are current.
- [ ] Migration behavior is documented.
- [ ] Known limitations are documented.
- [ ] Release notes are prepared.
- [ ] No generated artifacts such as `*.egg-info`, `dist/`, or SQLite DBs are
      committed.
- [ ] No runtime imports reference `ets.core.ets_core`.

Additional production gate:

- [ ] Production auth configured and tested.
- [ ] Production signing configured and tested.
- [ ] Backup/restore runbook validated.
- [ ] Incident response owner assigned.
- [ ] Dependency and secret scans reviewed.
- [ ] Docker federation validated with `scripts/validate-docker-federation.ps1`.
