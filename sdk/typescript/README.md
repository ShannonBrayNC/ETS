# @lanternprotocol/ets-sdk

TypeScript client for the ETS Application SDK v1 contract.

```ts
import { EtsClient } from "@lanternprotocol/ets-sdk";

const ets = new EtsClient({
  baseUrl: "https://ets.example/",
  bearerToken: process.env.ETS_TOKEN,
});

await ets.checkCompatibility();
```

For local development, plaintext HTTP is accepted only when explicitly enabled
for a loopback ETS Dev endpoint.

A successful capture receipt has only `commitment_state="committed_local"`.
It does not establish source truth, completeness, synchronization, authorization
standing, independent verification, or external anchoring.

See the repository `docs/sdk` directory for the compatibility contract and
cross-language conformance policy.
