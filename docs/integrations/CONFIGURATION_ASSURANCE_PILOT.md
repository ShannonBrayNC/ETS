# ETS configuration assurance pilot

Planning decision, 2026-11-07. Target a read-only Microsoft 365 drift assessment as an organizational pilot. Budget six working weeks from kickoff, contingent on access, staffing and the gates below. The existing governed SharePoint demonstration remains the first Agent 365 demonstration. This plan records proposed work and acceptance criteria.

## Scope and accountability

Select three disposable controls with stable target IDs: one Microsoft Graph Tenant Configuration Management (TCM) resource supported in the test tenant, one Microsoft365DSC property independently readable from its workload, and one cross-platform DSC 3 host property supported on the chosen OS. Assign a control owner and a single authorized writer per property. Use a reviewed Git revision for desired state. Treat discovered settings as baseline candidates until approved.

- WatchTower collects read-only findings. Pin OS, engine, adapters, module versions, API versions and permissions. Distinguish classic DSC 1.1 MOF/LCM, PowerShell DSC 2.x with Azure Machine Configuration, and standalone DSC 3 JSON/YAML workers. Microsoft365DSC manages tenant settings and has its own runtime prerequisites. Use test-only operations or Azure Machine Configuration Audit for initial assessments. ApplyAndMonitor may write on first assignment.
- QRF uses an Entra agent instance and approved MCP tools to investigate, correlate an exception or ticket, and propose an exact repair. Work IQ can locate authorized business context. The Microsoft OpenTelemetry Distro associates the agent invocation and tool spans with the case. Keep protected evidence out of span attributes.
- A separate pipeline identity may execute one approved repair in the disposable scope. Bind approval to tenant, resource, property diff, baseline digest and expiry. Re-read before writing, reject a competing edit, and read back before retrying a timeout. Capture rollback and partial failure. Use a separate reader for verification and record shared source dependencies.
- ETS preserves native observations before normalization using the [A365-Q0 contract](MICROSOFT_AGENT_365_Q0_SOURCE_CONTRACT.md). Record source/collection times, provenance, control and case IDs, engine versions, expected and observed state, exceptions, approvals, executor, retries and independent read-back. Link the agent's interpretation separately. Protect raw data, document redactions and sign a portable manifest. ETS Verify should reproduce the bounded result offline using trusted verification material.

## Six-week rollout and exit evidence

| Week | Accountable function | Deliverable and exit evidence |
| --- | --- | --- |
| 1 | Control owners and integration engineering | Coverage matrix for all three controls, tenant/license checks, reader and writer identities, collection intervals, exception expiry and data-handling decisions. Each control has a native read path and a disposable test target. |
| 2 | WatchTower and connector engineering | Show deliberate drift, a stable repeat observation and loss of collection authority. Emit unknown with last successful observation time for loss of access; distinguish unsupported and excepted. Archive TCM evidence before replacing a monitor baseline. |
| 3 | ETS Edge and Verify | Preserve raw observations and sign the manifest. A second engineer verifies it offline, detects tampering, and distinguishes a missing trust anchor from a changed artifact. |
| 4 | QRF and Agent 365 integration | Trace an investigation and proposal through the correct agent instance, invocation and tool calls to the ETS case. Prove the investigator lacks production write authority. |
| 5 | Change owner and deployment engineering | On one disposable target, exercise an approved repair, refused or expired approval, competing edit, timeout/read-before-retry, and rollback. Closure requires fresh target read-back; a behavioral claim also requires a bounded behavior test. |
| 6 | Qualification and customer enablement | Hand off baseline, coverage, exceptions, evidence and verifier instructions. An external reviewer distinguishes drift detected, collection unknown, repair attempted, state restored and effectiveness tested. Record gaps and a go/no-go decision. |

## Qualification and customer rollout

Reuse [A365-Q0 through Q5](MICROSOFT_AGENT_365_EVIDENCE_ACQUISITION.md): source preservation (Q0), authority (Q1), authentication/audit (Q2), runtime correlation (Q3), target consequence (Q4), independent verification (Q5). The week-three offline fixture is an early integration check; Q5 requires the complete live case. Track coverage against the specific gate and resource. A passing host fixture does not qualify a tenant integration.

Lead the customer demonstration with collection revoked → unknown, then show detected drift and verified repair. Record detection lag, age of last good observation, fraction of controls with independent read-back and reviewer time to verify. Report numerator, denominator and polling interval. A signed point-in-time sample cannot establish uninterrupted compliance.

Sequence follow-on offers by evidence: DSC 1.1/Azure Automation migration-equivalence assessment, agent identity/tool-access review, disconnected Edge host assurance, then incident recovery with verified read-back. Microsoft schedules Azure Automation State Configuration retirement for September 30, 2027. Compare legacy and replacement behavior per control before cutover. Scope any broader remediation offering after pilot review.

## Platform dependencies

- [DSC generations](https://learn.microsoft.com/en-us/powershell/scripting/dsc/overview), [DSC 3 tests](https://learn.microsoft.com/en-us/powershell/dsc/reference/cli/config/test?view=dsc-3.0), [Microsoft365DSC prerequisites](https://microsoft365dsc.com/user-guide/get-started/prerequisites/)
- [Graph TCM limits and retention](https://learn.microsoft.com/en-us/graph/api/resources/unified-tenant-configuration-management-api-overview?view=graph-rest-1.0): size the collection plan for six-hour evaluations and the tenant quota. Baseline updates remove previous monitor results and drifts.
- [Machine remediation modes](https://learn.microsoft.com/en-us/azure/governance/machine-configuration/concepts/remediation-options) and [migration guide](https://learn.microsoft.com/en-us/azure/governance/machine-configuration/whats-new/migrating-from-azure-automation): autocorrection can hide drift history from the ordinary compliance result.
- [Microsoft OpenTelemetry Distro](https://learn.microsoft.com/en-us/microsoft-agent-365/developer/microsoft-opentelemetry)
