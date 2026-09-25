# LanternProtocol.ETS.Application

.NET 8 client for the ETS Application SDK v1 contract.

```csharp
using Ets.Application;

using var ets = new EtsClient(new EtsClientOptions
{
    BaseUri = new Uri("https://ets.example/"),
    BearerToken = token,
});

await ets.CheckCompatibilityAsync();
```

The package keeps ETS transport semantics distinct from the existing
`Ets.Evidence` Evidence Object canonicalization library.

A successful append returns a `committed_local` receipt. That receipt is not a
claim of source truth, completeness, synchronization, authorization standing,
independent verification, or external anchoring.
