# ETS Console

ETS Console is the production-oriented browser surface for ETS operators, investigators, architects, auditors, and evidence producers.

It is intentionally separate from `apps/observatory`, which remains a research and demonstration environment.

## P1 scaffold

The current P1 branch establishes:

- a React + TypeScript + Vite production application boundary;
- explicit browser routing without adding a routing framework yet;
- typed ETS API contracts;
- tenant/workspace scope headers;
- Overview and runtime diagnostics;
- direct evidence lookup and evidence detail;
- browser file registration through `POST /evidence/register`;
- artifact receipt display;
- proof retrieval and JSON export;
- a human-readable verification-boundary statement;
- reserved Collectors, Administration, and URL-capture routes.

## Run locally

Start ETS API from the repository root:

```bash
python -m uvicorn ets.api.app:app --reload --port 8000
```

Then run the Console:

```bash
cd apps/console/web
npm install
npm run dev
```

Open `http://127.0.0.1:5174/`.

The Vite development proxy forwards ETS API routes to `http://127.0.0.1:8000`.

## Current security boundary

The P1 scaffold displays a development operator placeholder and editable tenant/workspace scope. That is **not production authentication or authorization**.

Before P1 can satisfy its production acceptance gate, Console must consume the approved hosted authentication profile, obtain server-derived identity/roles, and enforce administrative and tenant/workspace authorization on the server. Browser-side navigation and filtering are not authorization boundaries.

Production signing private keys and collector credentials must never be delivered to browser code.

## Verification boundary

ETS can verify declared cryptographic and provenance properties of submitted records and supplied proof material. Console must not represent registration, hashing, proof validity, or service health as proof of real-world truth, observation completeness, legal admissibility, or regulatory compliance.

## Next implementation steps

1. Add server-backed auth context and role-aware authorization behavior.
2. Add evidence inventory/list API integration and filters.
3. Add explicit proof verification result/reason-code rendering rather than proof-presence status.
4. Add unit, API-contract, accessibility, and end-to-end test gates.
5. Implement issue #210 Web Collector behind the reserved `/collect/url` workflow.
