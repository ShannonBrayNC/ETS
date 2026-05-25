# ETS Observatory

ETS Observatory is a human-readable research exhibit for visualizing ETS concepts in motion.

It is intentionally small in the first slice.

The goal is to make computationally bounded evidentiary coordination visible:

- evidence events;
- verifier nodes;
- root gossip;
- replay visibility;
- omission suspicion;
- partition state;
- confidence degradation;
- conflict preservation.

## Current Scope

This starter app includes:

- a deterministic FastAPI simulation backend;
- a static browser UI;
- a built-in baseline scenario;
- JSON APIs for observatory state;
- a timeline-oriented visualization.

It does not yet include:

- real distributed node execution;
- websocket streaming;
- persistent storage;
- production authentication;
- live transport simulation.

Those are future increments.

## Run Locally

From the repository root:

```bash
python -m pip install -e ".[dev]"
uvicorn apps.observatory.backend.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/
```

## API

```text
GET /api/observatory/scenario
GET /api/observatory/state
GET /api/observatory/timeline
```

## Research Purpose

The Observatory exists because ETS should not merely state that uncertainty, replay, omission, and disagreement matter.

It should show them.

Most systems hide epistemic uncertainty behind a green check mark.

ETS Observatory is designed to expose that uncertainty as a first-class protocol condition.
