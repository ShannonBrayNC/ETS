# ETS Generic REST Transport Profile v1

Status: G2H-A candidate  
Parent: #256  
Sprint: #298

## Purpose

Define the bounded source-transport boundary for the Generic REST connector before declarative
record extraction, checkpoint semantics, or Gateway commitment are added.

This profile deliberately solves source access only. It does not create evidence, choose ETS scope,
claim source completeness, or define a new persistence path.

## Server-owned trust policy

Credential-bearing REST requests require a `GenericRestHostPolicy` supplied by the trusted Gateway
composition layer. Customer connector settings may choose an endpoint only when its exact DNS host
is already present in that server-owned allow-list.

The v1 reference profile additionally requires:

- HTTPS;
- port 443;
- no URL user information;
- no fragment;
- no inline endpoint query string.

Static query values belong to the bounded request profile. This keeps the URL and request metadata
independently inspectable and prevents credentials from being redirected to a customer-selected
second host.

## Redirect policy

HTTP redirects are disabled. A redirect is not followed even when the target also uses HTTPS.
Changing the credential destination host requires an explicit server trust-policy change rather
than ordinary source response behavior.

## Credential boundary

The transport accepts credential bytes only from the future G2B-backed adapter/runner boundary.
Reusable values are never configuration fields. When credential material is supplied, the reference
transport injects it as an `Authorization: Bearer` header and keeps a mutable local copy that is
zeroized on `close()`.

Static customer headers and query parameters reject credential-like names including authorization,
token, secret, password, credential, private-key and API-key forms. That is a defense-in-depth
constraint; opaque credential references remain the supported reusable-authentication mechanism.

## Resource bounds

The reference request profile provides explicit limits for:

- timeout: `0.1..60` seconds;
- response body: `1..16 MiB`;
- static headers: at most 64;
- static query items: at most 64;
- metadata name length: at most 128 characters;
- metadata value length: at most 2048 characters.

Response reads request one byte beyond the configured maximum so an over-bound response fails
closed rather than being silently truncated and treated as a complete source response.

## Failure vocabulary

The transport exposes source-specific exceptions that the G2H adapter will map into the standard
connector operation codes:

- authentication failure;
- authorization failure;
- throttling with a bounded retry delay;
- retryable transport/source failure;
- terminal source rejection;
- redirect rejection;
- response-size rejection.

No failure path advances a source checkpoint in this layer because G2H-A does not own checkpoint
state.

## Separation from later G2H slices

G2H-A does **not** decide:

- where records live inside returned JSON;
- which fields are evidence-relevant;
- source record identity;
- source observation time;
- cursor or time-window checkpoint semantics;
- privacy/minimization transformation;
- ETS tenant/workspace;
- Gateway commitment or synchronization.

Those responsibilities remain #299 and #300. Third-party package integrity and provenance remain
#302.

## Nonclaims

A successful HTTP request means only that the qualified transport obtained a bounded response from
an authorized destination. It is not proof that the source is truthful, complete, continuous,
compliant, uncompromised, or cryptographically verified by ETS.
