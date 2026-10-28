# Industry evidence workflows: runnable synthetic recipes

These ten recipes adapt the existing Application SDK, not ten shipped industry
connectors. They demonstrate commitment, retrieval and verification of submitted
metadata. They do **not** certify compliance, establish legal sufficiency, make
clinical/financial decisions, prove physical truth or establish complete source coverage.

## Run any recipe end to end

Use a new output directory and an installed Python test-kit environment:

```powershell
python examples/sdk/python/offline_roundtrip.py --industry manufacturing --output ./qa-demo
```

Choices: `finance`, `healthcare`, `supplychain`, `manufacturing`, `insurance`,
`government`, `energy`, `ai`, `media`, `education`. The actual recipe data lives
in [`industry_recipes.json`](../../examples/sdk/python/industry_recipes.json).
Each run produces a fictional artifact, validated event, local append, signed
sample checkpoint, bundle, separate public trust file and strict CLI reports.
Expected results are signed **valid**, tampered **invalid**, missing trust
**indeterminate**, always with the appropriate checkpoint-only limitation.
Add `--deterministic-smoke` only for a PUBLIC test key and reproducible fixture
bytes; never for a production issuer. No private key is saved.

Every recipe is covered by the parameterized
[offline example tests](../../tests/unit/test_sdk_offline_example.py). The sample
uses an in-memory local log and synthetic text, not real devices, tenant services,
medical records, transactions, media assets or external providers. To adapt a recipe,
follow the same pipeline through Python `capture`/`bundle`, .NET
`CaptureAsync`/`GetBundleAsync`, or TypeScript `capture`/`getBundle`; .NET/TS
export bytes to the shared strict CLI, not nonexistent native verifier methods.
See the [task guide](TASK_GUIDE.md) for exact APIs and recovery requirements.

## Common design rules

- Decide exactly which artifact bytes or canonical structured representation
  `content_hash` commits. Retain those bytes separately and compare their SHA-256
  on retrieval; bundle verification does not fetch external content.
- Persist a stable event ID and exact intended payload before capture; retain
  receipt, bundle, trust-policy version and report. Duplicate/uncertain writes
  require reconciliation, not a new ID or an assumed exactly-once receipt.
- Use opaque references; minimize metadata. A hash/reference can still be sensitive
  or linkable. Do not treat hashing or pseudonyms as automatic anonymization.
- Production source identity, signing keys, independent observation, retention,
  access policies and required completeness are separate controls. A receipt is
  only `committed_local`; offline verification is only at the selected checkpoint.
- Capture revisions as new events linked by application-defined references.
  There is no SDK update/delete event API, universal consent engine or automatic
  retention enforcement. Review privacy/deletion obligations before committing
  identifying or regulated data to an append-only record.

## 1. Finance: reconciliation report revisions

**Task:** retain a verifiable reference to each produced reconciliation report.
Run `--industry finance`. Event type is `finance.reconciliation.completed`;
subject `recon-demo-01`; fields include `statement_ref`, `period`, `currency`
and integer `amount_minor`. For real integration, hash the exact report bytes
and use an independently controlled statement/reference ID, never account numbers
or payment credentials. Model corrections with a new revision event.

**Development work:** capture one event per report, retain receipt; retrieve
bundle; verify expected log and signer; compare downloaded report bytes to
`content_hash`; export the strict result for the review workflow. Use integers
in minor units or explicit decimal strings, not floating-point monetary arithmetic.

**Negative/uncertain test:** change the committed amount or swap a report file;
the former fails bundle checks, the latter must fail the separate content digest
comparison. Simulate a timed-out capture and reconcile the original event ID.
**Not established:** settlement, balance/account correctness, authorization,
fraud absence, audit/regulatory compliance or financial advice.

## 2. Healthcare: synthetic document/consent revision tracking

**Task:** track versions of a synthetic workflow document without patient data.
Run `--industry healthcare`. Type `healthcare.document.revision`; opaque subject
`patient-demo-opaque`; metadata `document_kind`, `revision`, `workflow_ref`.
Store real sensitive documents only in separately authorized systems; do not
place PHI, names, dates of birth or free-form clinical notes in this example.

**Development work:** hash exact approved document representation; capture a new
event for each revision; retrieve the selected version's bundle and verify;
record business consent/authorization state separately from cryptographic checks.

**Negative/uncertain test:** show that an older signed revision can remain
cryptographically valid even after a later revocation/business decision. Test
wrong workspace/role denial and ensure logs never reveal document contents.
**Not established:** consent authority, clinical accuracy, HIPAA/GDPR compliance,
current authorization or medical fitness. Obtain qualified privacy/security review
before committing any regulated or re-identifiable information.

## 3. Supply chain: observed handoff records

**Task:** commit a sequence of independently supplied handoff manifests.
Run `--industry supplychain`. Type `supplychain.custody.observed`; subject
`shipment-demo`; metadata `lot_ref`, `checkpoint_ref`, `sequence`.
Use separate actor/source references rather than representing a client string as
verified identity. Retain the manifest bytes and the basis for each observation.

**Development work:** capture each observation with stable source sequence;
retrieve known event IDs, compare expected sequence in application logic, export
bundles and verify checkpoint signatures. The SDK does not supply atomic batches,
source completeness or an authoritative physical-custody model.

**Negative/uncertain test:** omit a checkpoint. Remaining bundles can verify, so
an external expected-event policy must detect the missing step. Tamper a handoff
record and confirm strict failure. **Not established:** physical possession,
product authenticity, complete custody or sensor/source truth.

## 4. Manufacturing: inspection and calibration references

**Task:** preserve inspection artifact revisions and declared calibration context.
Run `--industry manufacturing`. Type `manufacturing.inspection.recorded`; subject
`batch-demo`; metadata `device_ref`, `calibration_ref`, `inspection_ref`.
Hash the actual inspection CSV/report separately; a declared calibration reference
is not evidence that a gauge was calibrated or correctly used.

**Development work:** validate/minimize metadata, append/capture, retain bundle
and public-trust policy, compare artifact hash, verify and export pass/fail report.
Retain independent calibration and physical-result evidence where claims need it.

**Negative/uncertain test:** change inspection metadata after commit; remove trust;
use a valid signed but out-of-date calibration reference and ensure business logic
does not call that qualified measurement. **Not established:** measurement accuracy,
physical quality, certification or safety compliance. ETS does not control machinery.

## 5. Insurance: attachment and adjuster-version integrity

**Task:** record synthetic claim attachment versions for later comparison.
Run `--industry insurance`. Type `insurance.claim.attachment`; subject `claim-demo`;
metadata `attachment_ref`, `revision`, `media_type`. Keep claim identities,
medical details and evidence content outside the log under independent controls.

**Development work:** capture a new event per attachment revision, link prior
revision in minimized application metadata, retrieve bundle, hash actual attachment,
strictly verify selected issuer/log, and retain the report with review state.

**Negative/uncertain test:** exchange attachment bytes while keeping the bundle
unchanged; the separate digest check must catch it. Reconcile duplicate uploads
without generating accidental new events. **Not established:** eligibility,
coverage, causation, claim truth, fraud absence or adjudication correctness.

## 6. Public sector: record-revision transparency

**Task:** preserve integrity of public/synthetic record versions.
Run `--industry government`. Type `government.record.revision`; subject
`record-demo`; metadata `department_ref`, `revision`, `retention_class`.
Use fictional records during testing; a `retention_class` field is merely metadata,
not implementation of a records-retention schedule.

**Development work:** publish/export the intended record bytes, commit their hash,
retrieve bundle, verify with explicitly selected public issuer trust and export a
checkpoint-only report. Define accessibility, disclosure and records policies
outside the SDK. This is not voting/tabulation software or an official record system.

**Negative/uncertain test:** alter a revision; remove a required record from an
external expected-record inventory; show that omission needs that external policy.
**Not established:** legal admissibility, official disposition, retention compliance,
complete records disclosure, government endorsement or election correctness.

## 7. Energy/IoT: maintenance observation sequences

**Task:** retain synthetic maintenance report and device-reference observations.
Run `--industry energy`. Type `energy.maintenance.recorded`; subject `asset-demo`;
metadata `work_order_ref`, `meter_ref`, `sequence`. Do not embed control credentials,
network locations or critical-infrastructure secrets.

**Development work:** capture bounded observations, persist outbox/retry state
when disconnected, reconcile each event ID, export bundles and compare reports.
An SDK outbox/offline synchronization agent is **not** supplied; enterprise Edge
and physical hardware qualification remain separate products/work.

**Negative/uncertain test:** duplicate a source sequence or submit after a simulated
transport failure; application logic must detect/reconcile rather than assume
exactly-once delivery. **Not established:** physical safety, sensor accuracy,
calibration, uptime, emissions compliance or independent real-world observation.

## 8. Enterprise AI/software: evaluation and release artifacts

**Task:** link a synthetic evaluation artifact to declared model/build/dataset
references. Run `--industry ai`. Type `ai.release.evaluation`; subject `model-demo`;
metadata `release_ref`, `dataset_ref`, `evaluation_ref`, `build_ref`. In a real
integration commit separately retained artifact digests and tool/version context,
without prompts, secrets or customer/model training data in public metadata.

**Development work:** use a CI producer identity, capture artifact metadata,
retain receipt/bundle, independently verify with a reviewer trust policy, and
compare test/evaluation bytes against their hashes. Model tool-call, authorization
and observed outcome as distinct records when needed; correlation is not proof
that a downstream M365/SharePoint or physical operation succeeded.

**Negative/uncertain test:** swap the evaluation artifact; reuse an event ID with
a different build; omit an expected test run. Each needs the appropriate digest,
conflict or completeness policy. **Not established:** model safety, dataset legality,
complete provenance, test adequacy, tool success or Agent 365 tenant qualification.
This recipe is not a bundled Microsoft connector or permission grant.

## 9. Media: asset version and license-reference integrity

**Task:** preserve exact asset-version hashes and declared license-record references.
Run `--industry media`. Type `media.asset.version`; subject `asset-demo`;
metadata `revision`, `license_record_ref`. Hash exact image/audio/video bytes;
transcoding, metadata editing or recompression intentionally changes that digest.

**Development work:** capture each version, store bytes externally, export its
bundle and verify; separately evaluate license/source identity and the intended
presentation. Add a new event for transformations instead of claiming two
different byte streams are the same content hash.

**Negative/uncertain test:** transcode a copy and verify its digest differs; supply
a valid bundle signed by an untrusted key and require non-success.
**Not established:** authorship, ownership, copyright permission, authenticity of
what is depicted, absence of AI generation or C2PA interoperability.

## 10. Education/games/research: credential and observation revisions

**Task:** preserve synthetic credential-document revisions. Run `--industry
education`. Type `education.credential.revision`; subject `learner-demo-opaque`;
metadata `credential_ref`, `issuer_ref`, `revision`. Keep student identity and
sensitive educational records outside the example. For games, the existing
[Chess walkthrough](../../examples/sdk/chess/README.md) demonstrates move telemetry,
but uses the unsigned Dev profile and must not be described as strict issuer trust.

**Development work:** capture revision/observation records, retrieve bundles,
verify at a selected checkpoint, compare original artifact bytes, and preserve
application-level current standing separately. Research dataset revisions use the
same integrity pipeline but need their own ethics/licensing/reproducibility policy.

**Negative/uncertain test:** an old credential version can verify after its issuer
revokes business validity; enforce current standing independently. For games,
submitted move observations do not prove a physical move or fair play.
**Not established:** identity, accreditation, attainment, enrollment consent,
research validity, current credential status or game-result correctness.

## Before adapting any recipe to real data

Assign data/security owners, review source authorization, privacy and retention,
qualify the real issuer/trust store and deployed endpoint, test negative cases,
retain exact package/schema/policy versions, and obtain the required release/IP
approvals. Never reuse sample trust or public smoke keys for real evidence.
