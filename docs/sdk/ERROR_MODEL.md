# ETS Application SDK error model

The Application SDK uses a transport-neutral error vocabulary so Python, .NET,
and TypeScript clients can expose equivalent failure classes even when HTTP,
local, or future transports differ.

Stable SDK error codes:

- `transport_error`
- `authentication_failed`
- `authorization_failed`
- `not_found`
- `conflict`
- `validation_failed`
- `request_too_large`
- `server_error`
- `unsafe_configuration`
- `incompatible_version`
- `unknown_error`

The Python `classify_api_error()` helper maps current API codes/statuses into
this vocabulary.

The normalized error is operational state, not evidence verification state. An
HTTP success is not proof validity, and an operational failure does not permit a
client to synthesize or guess an ETS verification result.
