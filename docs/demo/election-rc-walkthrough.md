# ETS Election RC Demo Walkthrough

The election-security RC demo is a fictional, public-safe workflow for showing
how ETS records election-adjacent evidence metadata, publishes a Merkle root,
verifies an inclusion proof, and rejects a tampered proof.

ETS is an evidence and audit layer. It is not voting software, tabulation
software, voter registration software, or the vote of record.

## One-Command Demo

From the repository root on Windows PowerShell:

```powershell
.\scripts\run-election-rc-demo.ps1
```

Equivalent Python module form:

```powershell
.\.venv\Scripts\python.exe -m ets.election.rc_demo
```

The command writes deterministic artifacts to `artifacts/election-rc-demo/`:

- `root-manifest.json`
- `audit-log.json`
- `proof-bundle.json`
- `verification-result.json`
- `tamper-result.json`
- `walkthrough.md`

## Demo Storyboard

1. Import fictional election setup package.
2. Register logic and accuracy evidence.
3. Register ballot batch custody transfers.
4. Generate milestone Merkle root.
5. Publish public proof.
6. Verify valid evidence packet.
7. Demonstrate tampered artifact rejection.
8. Export audit package.

## Explorer Visual Path

The Explorer UI includes an election RC panel that mirrors the same storyboard:

- audit timeline
- milestone Merkle root
- inclusion proof view
- chain integrity status
- public/restricted artifact indicators
- red failure state for the tampered proof

Run the Explorer build check:

```powershell
Set-Location ets\explorer-ui
npm run build
Set-Location ..\..
```

## Privacy Boundary

The demo stores fictional metadata and content hashes only. It does not store
raw ballots, voter records, tabulation output, private keys, or real personally
identifying information.
