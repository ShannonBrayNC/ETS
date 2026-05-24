# ETS Explorer RC Walkthrough

This walkthrough shows the local RC demo path for the Explorer UI.

## Start the API

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
$env:ETS_STORAGE_PROVIDER = "sqlite"
$env:ETS_SQLITE_PATH = ".data\ets-demo.db"
.\.venv\Scripts\python.exe -m uvicorn ets.api.app:app --reload --port 8000
```

## Start the Explorer

```powershell
Set-Location ets\explorer-ui
npm ci
npm run dev
```

Open the Vite local URL in the browser.

## Demo flow

1. Confirm the API base URL is `http://localhost:8000`.
2. Use the default tenant/workspace values or set your own.
3. Select **Check health**.
4. Select **Append sample event**.
5. Select the generated event ID from the Events table.
6. Select **Get proof**.
7. Select **Verify**.
8. Select **Generate** to create a Markdown certificate payload.
9. Copy or download the proof and certificate artifacts.

## Expected talking points

- ETS stores evidence metadata and hashes, not raw evidence bytes.
- The demo event is fictional and safe to commit or share.
- The proof proves the event hash is included in the current local Merkle tree.
- Unsigned local tree heads are demo metadata, not production trust anchors.
- Hosted deployments should use the JWKS auth profile and production signing guidance.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| API Error appears immediately | API is not running | Start uvicorn on port 8000 |
| Browser CORS error | API origin restrictions changed | Confirm local API CORS settings |
| `401` response | Auth mode requires token or API key | Paste token/API key into Connection panel |
| Empty Events table | No events appended in current store | Use **Append sample event** |
| Proof button disabled | No event selected | Click an Event ID in the table |

## Cleanup

To reset the demo database:

```powershell
Remove-Item .data\ets-demo.db -ErrorAction SilentlyContinue
```
