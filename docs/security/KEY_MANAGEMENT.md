# ETS Key Management

RC signing supports explicit local unsigned mode and optional Ed25519 signing.
Unsigned mode is for development only.

Production signing requirements before hosted release:

- private keys are generated and stored outside the repository;
- key IDs are stable and published with tree heads;
- rotation is documented and tested;
- compromised keys can be revoked without rewriting historical evidence;
- startup fails if production signing is requested without a signer.

Production API authentication can be configured with RS256 JWKS verification
through `ETS_AUTH_MODE=production_jwks`. Hosted deployments should prefer a
managed OIDC issuer and JWKS URL over static JWKS JSON.
