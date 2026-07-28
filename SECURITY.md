# Security Policy

ETS is an alpha-stage Evidence Transparency System. Please treat this repository
as public infrastructure code and public protocol documentation, not as a place
to submit sensitive evidence.

## Supported Versions

| Version | Supported |
|---|---|
| `v0.1.0-alpha` | Security reports accepted; production support is not implied. |
| Unreleased `main` | Security reports accepted. |

## Reporting a Vulnerability

Please open a private security advisory when available, or contact the project
maintainer through a private channel. Do not disclose exploitable vulnerabilities
in public issues before the maintainer has had time to review and respond.

Include:

- affected component;
- reproduction steps using synthetic data;
- expected result;
- actual result;
- impact assessment;
- suggested mitigation, if known.

## Public Evidence Boundary

Do not submit real secrets, real PII, live credentials, private keys, production
customer evidence, official election data, legally sensitive evidence, medical
records, financial records, or restricted incident records through public issues or pull requests.

Use synthetic fixtures only. If a bug requires sensitive reproduction material,
describe the structure of the data without exposing the data itself.

## Patent and Legal Boundary

Do not submit USPTO receipts, application numbers, confirmation numbers,
provisional drafts, claim charts, prior-art matrices, attorney-review notes, or
assignment strategy in public issues, discussions, examples, tests, or pull
requests.

## Cryptographic Boundary

ETS uses standard cryptographic primitives in the alpha implementation. Reports
that identify misuse, weak key handling, ambiguous verification semantics,
replay/fork handling gaps, or unsafe defaults are welcome.

## Non-Claims

ETS does not prove real-world truth, legal sufficiency, official chain of
custody, election correctness, vote totals, ballot validity, or completeness
without external policy and observation.
