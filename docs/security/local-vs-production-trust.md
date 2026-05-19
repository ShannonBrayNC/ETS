# Local vs Production Trust

The default ETS API mode is local and unsigned. A local unsigned tree head is
useful for development and deterministic verifier testing, but it is not a
production trust anchor.

`ETS_SIGNING_MODE=local_unsigned` is the default alpha mode. `ed25519` and
`production` modes require `ETS_SIGNING_PRIVATE_KEY_HEX` and
`ETS_SIGNING_PUBLIC_KEY_ID`; startup fails if signing is requested without key
configuration.

`ETS_AUTH_MODE=production_jwt` requires `ETS_AUTH_HS256_SECRET` and rejects
unauthenticated `/api/v1/*` requests. Tokens must be HS256 bearer tokens with an
`exp` claim. Optional `tenant_id` and `workspace_id` claims constrain the request
scope and must match supplied tenant/workspace headers.

Future production deployments should use a configured signing backend, protected
keys, authenticated tenant boundaries, and client-side checkpoint retention.
