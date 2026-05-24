# ETS Patent Preparation Diagrams

These diagrams are technical review aids for patent counsel. They are not legal advice and
are not filed patent figures.

## Evidence Lifecycle

```mermaid
flowchart TD
  A["Evidence source"] --> B["Canonical evidence event"]
  B --> C["Hash and redact"]
  C --> D["Append-only log"]
  D --> E["Proof bundle"]
  E --> F["Verifier"]
```

## Verifier Federation Topology

```mermaid
flowchart LR
  L1["Transparency node 1"] --> V1["Verifier 1"]
  L2["Transparency node 2"] --> V1
  L2 --> V2["Verifier 2"]
  L3["Transparency node 3"] --> V2
  W["Witness"] --> V1
  W --> V2
```

## Omission Suspicion Workflow

```mermaid
flowchart TD
  E["Expected event policy"] --> C["Compare expected IDs to observed IDs"]
  O["Observed transparency log"] --> C
  C --> F["Omission findings"]
  F --> R["Review and remediation"]
```

## AI Accountability Evidence Chain

```mermaid
flowchart TD
  P["Prompt hash"] --> A["AI evidence event"]
  M["Model metadata"] --> A
  O["Output hash"] --> A
  A --> L["Log append"]
  L --> B["Proof bundle"]
  B --> V["Independent verifier"]
```

## Multi-Node Transparency Architecture

```mermaid
flowchart TD
  S["Evidence SDK/API"] --> L1["Log node A"]
  S --> L2["Log node B"]
  S --> L3["Log node C"]
  L1 --> W["Witness"]
  L2 --> W
  L3 --> W
  W --> Q["Verifier quorum"]
```

## Selective Disclosure Verification

```mermaid
flowchart LR
  Private["Restricted evidence"] --> Hash["Public hash"]
  Hash --> Proof["Public proof"]
  Proof --> Verifier["Public verifier"]
  Private --> Reviewer["Authorized reviewer"]
```
