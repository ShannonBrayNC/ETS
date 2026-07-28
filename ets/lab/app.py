"""FastAPI UI for the ETS Python testing lab."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from ets.lab.scenarios import (
    CLAIM_BOUNDARY,
    list_components,
    list_scenarios,
    run_consistency_progression_demo,
    run_lab_scenario,
)
from ets.version import __version__


LAB_HTML = r"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>ETS Python Testing Lab</title>
  <style>
    :root {
      color-scheme: light dark;
      --bg: #0f172a;
      --panel: #111827;
      --card: #1f2937;
      --muted: #94a3b8;
      --text: #e5e7eb;
      --accent: #38bdf8;
      --ok: #34d399;
      --warn: #fbbf24;
      --bad: #fb7185;
      --border: #334155;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: radial-gradient(circle at top left, rgba(56, 189, 248, 0.18), transparent 32rem), var(--bg);
      color: var(--text);
    }
    main { max-width: 1180px; margin: 0 auto; padding: 2rem; }
    header { display: grid; gap: 0.75rem; margin-bottom: 1.5rem; }
    h1 { margin: 0; font-size: clamp(2rem, 5vw, 4rem); line-height: 1; }
    h2 { margin: 0 0 0.75rem; }
    p { color: var(--muted); line-height: 1.55; }
    .grid { display: grid; gap: 1rem; }
    .metrics { grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); }
    .columns { grid-template-columns: minmax(260px, 0.9fr) minmax(320px, 1.6fr); align-items: start; }
    .card, .component, .scenario, .result-panel {
      border: 1px solid var(--border);
      border-radius: 1rem;
      background: rgba(17, 24, 39, 0.86);
      padding: 1rem;
      box-shadow: 0 16px 40px rgba(0,0,0,0.25);
    }
    .metric-value { font-size: 1.65rem; font-weight: 800; color: var(--accent); }
    .metric-label { color: var(--muted); font-size: 0.9rem; }
    .component { display: grid; gap: 0.4rem; }
    .component strong { color: white; }
    .tag { display: inline-flex; align-items: center; width: fit-content; border: 1px solid var(--border); border-radius: 999px; padding: 0.15rem 0.55rem; color: var(--accent); font-size: 0.8rem; }
    .scenario { width: 100%; text-align: left; color: var(--text); cursor: pointer; }
    .scenario:hover, .scenario.active { border-color: var(--accent); background: rgba(14, 165, 233, 0.12); }
    .scenario-title { font-weight: 800; margin-bottom: 0.35rem; }
    .button-row { display: flex; gap: 0.75rem; flex-wrap: wrap; margin: 1rem 0; }
    button.primary {
      border: 0;
      border-radius: 999px;
      padding: 0.75rem 1rem;
      background: var(--accent);
      color: #082f49;
      font-weight: 800;
      cursor: pointer;
    }
    button.secondary {
      border: 1px solid var(--border);
      border-radius: 999px;
      padding: 0.75rem 1rem;
      background: transparent;
      color: var(--text);
      cursor: pointer;
    }
    .step { display: grid; grid-template-columns: 1rem 1fr; gap: 0.75rem; margin: 0.8rem 0; }
    .dot { width: 0.75rem; height: 0.75rem; border-radius: 99px; margin-top: 0.35rem; background: var(--muted); }
    .dot.passed { background: var(--ok); }
    .dot.failed { background: var(--bad); }
    .dot.informational { background: var(--warn); }
    pre {
      overflow: auto;
      max-height: 440px;
      border: 1px solid var(--border);
      border-radius: 1rem;
      background: #020617;
      color: #d1fae5;
      padding: 1rem;
      font-size: 0.82rem;
      line-height: 1.4;
    }
    .boundary { border-left: 4px solid var(--warn); background: rgba(251, 191, 36, 0.08); }
    .muted { color: var(--muted); }
    @media (max-width: 860px) {
      main { padding: 1rem; }
      .columns { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
<main>
  <header>
    <span class="tag">Evidence Transparency System · Python lab</span>
    <h1>Break down ETS, then run it.</h1>
    <p>
      This local lab demonstrates the ETS alpha pipeline: source events, canonicalization,
      EvidenceEvent validation, append-only logging, Merkle proofs, verification certificates,
      policy routing, and claim-safe boundaries.
    </p>
  </header>

  <section class="grid metrics" aria-label="Lab metrics">
    <div class="card"><div class="metric-value" id="componentCount">—</div><div class="metric-label">protocol components</div></div>
    <div class="card"><div class="metric-value" id="scenarioCount">—</div><div class="metric-label">demo scenarios</div></div>
    <div class="card"><div class="metric-value">v<span id="version">—</span></div><div class="metric-label">ETS package</div></div>
  </section>

  <section class="grid columns" style="margin-top: 1rem;">
    <div class="grid">
      <div class="card">
        <h2>Components</h2>
        <p>Each component maps to the provisional drawing figures and an executable demo capability.</p>
        <div id="components" class="grid"></div>
      </div>
    </div>
    <div class="grid">
      <div class="card">
        <h2>Demo scenarios</h2>
        <p>Select a scenario, then run it against the in-process Python scenario engine.</p>
        <div id="scenarios" class="grid"></div>
        <div class="button-row">
          <button class="primary" id="runButton" type="button">Run selected scenario</button>
          <button class="secondary" id="treeButton" type="button">Run tree-head progression demo</button>
        </div>
      </div>
      <div class="result-panel" aria-live="polite">
        <h2 id="resultTitle">No scenario run yet</h2>
        <p id="resultSummary" class="muted">Pick a scenario to light the lab lantern.</p>
        <div id="steps"></div>
        <pre id="outputs">{}</pre>
      </div>
      <div class="card boundary">
        <h2>Claim boundary</h2>
        <p id="claimBoundary"></p>
      </div>
    </div>
  </section>
</main>
<script>
const state = { scenarios: [], selected: "full-pipeline" };

function text(value) { return String(value ?? ""); }

async function loadLab() {
  const [meta, components, scenarios] = await Promise.all([
    fetch("/lab/api/meta").then(r => r.json()),
    fetch("/lab/api/components").then(r => r.json()),
    fetch("/lab/api/scenarios").then(r => r.json())
  ]);
  document.getElementById("componentCount").textContent = components.length;
  document.getElementById("scenarioCount").textContent = scenarios.length;
  document.getElementById("version").textContent = meta.version;
  document.getElementById("claimBoundary").textContent = meta.claim_boundary;
  state.scenarios = scenarios;
  renderComponents(components);
  renderScenarios(scenarios);
}

function renderComponents(components) {
  const root = document.getElementById("components");
  root.innerHTML = "";
  for (const item of components) {
    const node = document.createElement("article");
    node.className = "component";
    node.innerHTML = `<span class="tag">${text(item.figure)}</span><strong>${text(item.name)}</strong><span class="muted">${text(item.role)}</span><span>${text(item.demo_capability)}</span>`;
    root.appendChild(node);
  }
}

function renderScenarios(scenarios) {
  const root = document.getElementById("scenarios");
  root.innerHTML = "";
  for (const item of scenarios) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `scenario ${item.scenario_id === state.selected ? "active" : ""}`;
    button.dataset.scenario = item.scenario_id;
    button.innerHTML = `<div class="scenario-title">${text(item.title)}</div><div class="muted">${text(item.capability)}</div><div class="tag" style="margin-top:.5rem;">${item.figure_refs.map(text).join(" · ")}</div>`;
    button.addEventListener("click", () => {
      state.selected = item.scenario_id;
      renderScenarios(state.scenarios);
    });
    root.appendChild(button);
  }
}

function renderResult(result) {
  document.getElementById("resultTitle").textContent = result.title;
  document.getElementById("resultSummary").textContent = result.summary;
  const stepsRoot = document.getElementById("steps");
  stepsRoot.innerHTML = "";
  for (const step of result.steps) {
    const row = document.createElement("div");
    row.className = "step";
    row.innerHTML = `<div class="dot ${text(step.status)}"></div><div><strong>${text(step.name)}</strong><br><span class="muted">${text(step.detail)}</span></div>`;
    stepsRoot.appendChild(row);
  }
  document.getElementById("outputs").textContent = JSON.stringify(result.outputs, null, 2);
}

async function runSelected() {
  const result = await fetch(`/lab/api/run/${state.selected}`, { method: "POST" }).then(r => r.json());
  renderResult(result);
}

async function runTreeProgression() {
  const result = await fetch("/lab/api/tree-head-progression", { method: "POST" }).then(r => r.json());
  renderResult({
    title: "Tree-head progression demo",
    summary: "Generated a compact consistency proof and recomputed the latest Merkle root.",
    steps: [
      { name: "Previous tree size", status: "passed", detail: String(result.previous_tree_size) },
      { name: "Latest tree size", status: "passed", detail: String(result.latest_tree_size) },
      { name: "Consistency verification", status: result.verification.valid ? "passed" : "failed", detail: result.verification.reason }
    ],
    outputs: result
  });
}

document.getElementById("runButton").addEventListener("click", runSelected);
document.getElementById("treeButton").addEventListener("click", runTreeProgression);
loadLab().then(runSelected).catch(error => {
  document.getElementById("resultTitle").textContent = "Lab failed to load";
  document.getElementById("resultSummary").textContent = error.message;
});
</script>
</body>
</html>
"""


def create_lab_app() -> FastAPI:
    """Create the ETS lab UI application."""

    app = FastAPI(
        title="ETS Python Testing Lab",
        version=__version__,
        description="Interactive local testing lab for ETS protocol components and demos.",
    )

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    @app.get("/lab", response_class=HTMLResponse, include_in_schema=False)
    def lab_home() -> str:
        return LAB_HTML

    @app.get("/lab/api/meta")
    def meta() -> dict[str, str]:
        return {"version": __version__, "claim_boundary": CLAIM_BOUNDARY}

    @app.get("/lab/api/components")
    def components() -> list[dict[str, str]]:
        return list_components()

    @app.get("/lab/api/scenarios")
    def scenarios() -> list[dict[str, object]]:
        return list_scenarios()

    @app.post("/lab/api/run/{scenario_id}")
    def run_scenario(scenario_id: str) -> dict[str, object]:
        return run_lab_scenario(scenario_id).to_public_dict()

    @app.post("/lab/api/tree-head-progression")
    def tree_head_progression() -> dict[str, object]:
        return run_consistency_progression_demo()

    return app


app = create_lab_app()
