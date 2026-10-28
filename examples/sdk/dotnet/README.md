# .NET installed-package quickstart

Use the [task guide](../../../docs/sdk/DOTNET_CLIENT.md) for package build/restore,
authentication, live capture, errors and verification instructions.

The project references the pinned NuGet package, not SDK source. Smoke mode:

```powershell
dotnet run --no-restore --project examples/sdk/dotnet/Quickstart.csproj -- --smoke tests/fixtures/verifier/native-signed.json ./dotnet-bundle.json
```

Pass a new output filename. Smoke responses are synthetic and no network is used;
verify the exported fixture separately with the common CLI and public test trust.
`--live <new-output.json>` performs an explicitly configured real append and must
only be used in an authorized test workspace. No registry publication is required.
