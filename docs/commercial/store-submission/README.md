# ETS Desktop Developer: Store submission preparation

Prepared 2026-10-28. **DRAFT. NOT READY TO UPLOAD. NO SUBMISSION PERFORMED.**

This folder turns the partial alpha Developer candidate into reviewable submission
files. It does not approve a release, reserve a name, accept terms, publish a
privacy policy, sign/install software, change trust, or submit to Microsoft.
The ZIP contains preparation documents and synthetic test data, **not an MSIX**.

## Start here tomorrow

1. Fill [OWNER-DECISIONS.json](OWNER-DECISIONS.json). Do not paste unfilled fields
   into Partner Center. Name, publisher, public privacy URL and pricing cannot be
   inferred from GitHub or from the free standalone Verifier.
2. Review [copy-ready listing](listing/COPY-READY.txt) and its canonical
   [structured draft](listing/en-us.json). This describes only the implemented
   fixed sample, strict verifier/report export and alpha SDK kit, not the broader
   planned workbench. Recheck against the exact final package before use.
3. Read [package gates](PACKAGE-CHECKLIST.md) and [evidence matrix](EVIDENCE-MATRIX.md).
   The current engineering package is unsigned, uninstalled in retained CI
   evidence, and uses a development identity. There is no production manifest here.
4. Complete [assets](assets/ASSET-MANIFEST.json). No compliant native Windows
   screenshots or owner-approved Store branding are supplied. Browser regression
   screenshots are not submission assets.
5. Approve and publish the [privacy draft](PRIVACY-DRAFT.md) and
   [support draft](SUPPORT-DRAFT.md) through a separately authorized action, then
   verify their public destinations. Privacy is required for this Win32 app.
6. Use [reviewer instructions](REVIEWER-INSTRUCTIONS.md) and the concise
   [capability rationale](RUN-FULL-TRUST.txt), after exact-candidate qualification.
   Keep a manual publication hold if the owner chooses one; do not rely on default
   publish-after-certification behavior.

## Preparation completeness, not release readiness

| Ready for owner review | Remaining upload, submission and release gates |
| --- | --- |
| Listing copy, field-length checks, capability explanation | Reserved name and exact Partner Center identity |
| Repeatable synthetic reviewer path and expected outcomes | Owner-approved production version/build and retained digest |
| Draft privacy/support content and decision worksheet | Approved public privacy URL; support owner/contact |
| Screenshot shot list and asset validation requirements | Native final-candidate screenshots; approved icon |
| Existing evidence references and exact hash pins | Developer clean-client/lifecycle/runtime/accessibility testing; WACK |
| Portable validation helper and test-only fixture | Payload+SDK licensing/SBOM/IP review; Microsoft certification |

## Evidence boundary

Implementation: [draft PR #952](https://github.com/ShannonBrayNC/ETS/pull/952), head
`d3b4b7ceab63a1d251b92a2cda4fdbe753cb6d3f`; Windows candidate source
`2606424f61a8791bb1afc8169629f8390e849def`. SDK dependency:
[draft PR #951](https://github.com/ShannonBrayNC/ETS/pull/951), pinned packaged source
`a6eb2c70b4e84cdae5f6d88e788d2fb1f663fa3e`.
[Draft PR #950](https://github.com/ShannonBrayNC/ETS/pull/950) is the broader plan,
not the implemented feature set. None is merged as of this preparation.

The standalone Verifier's Lenovo 0.1.1.0 operator evidence is separate and is not
Developer Edition qualification. This folder does not duplicate or replace that
qualification ledger. Consult the repository's existing Windows release-gap,
Lenovo qualification and WACK handoff documents for their respective scope.

## Validate these preparation files

From this folder, run `python validate-prep.py` (standard library only). It checks
field lengths, decision nulls, fixture hashes, expected outcomes, local links and
asset blockers. A pass means this draft is internally consistent, not Store-ready.
Run `python validate-prep.py --require-ready` to confirm that release gates fail
closed. The expected current result is nonzero with the unresolved gates listed.

[Microsoft sources and policy notes](MICROSOFT-SOURCES.md) were checked
2026-10-28. Recheck the live Partner Center fields and policy before submission.
