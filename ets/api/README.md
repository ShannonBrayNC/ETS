# ETS API

FastAPI service for the ETS (Evidence Trust System) transparency log.

---

## 🚀 Endpoints

- `GET /healthz`
- `POST /events`
- `GET /events/{event_id}`
- `GET /tree-head`
- `GET /proof/{event_id}`
- `POST /verify/payload?event_id=<event_id>`

---

## 🧪 Local Run

### Install dependencies

```powershell
python -m pip install -r .\ets\api\requirements.txt