# TypeScript SDK installed-package quickstart (Node ESM)

Use the [task guide](../../../docs/sdk/TYPESCRIPT_CLIENT.md) for building/installing
the local tarball, configuring live capture, limitations and independent verification.

```powershell
node examples/sdk/typescript/quickstart.mjs --smoke tests/fixtures/verifier/native-signed.json ./ts-bundle.json
```

The `.mjs` example runs the TypeScript-authored package through its public package
import, without needing a compiler for the example itself. Pass a new output path.
Smoke transport responses are synthetic and use no network. `--live <new-output.json>`
performs a real append to an explicitly configured, authorized test workspace.
