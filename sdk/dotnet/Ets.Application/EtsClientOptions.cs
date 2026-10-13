namespace Ets.Application;

public sealed class EtsClientOptions
{
    public required Uri BaseUri { get; init; }
    public string? ApiKey { get; init; }
    public string? BearerToken { get; init; }
    public string? TenantId { get; init; }
    public string? WorkspaceId { get; init; }
    public bool AllowInsecureLoopbackHttp { get; init; }
    public TimeSpan Timeout { get; init; } = TimeSpan.FromSeconds(10);

    internal void Validate()
    {
        if (!BaseUri.IsAbsoluteUri || BaseUri.Scheme is not ("https" or "http"))
            throw new EtsApplicationException("unsafe_configuration", "BaseUri must be an absolute HTTP(S) URI.");
        if (ApiKey is not null && BearerToken is not null)
            throw new EtsApplicationException("unsafe_configuration", "ApiKey and BearerToken are mutually exclusive.");
        if ((TenantId is null) != (WorkspaceId is null))
            throw new EtsApplicationException("unsafe_configuration", "TenantId and WorkspaceId must be configured together.");
        if (BearerToken is not null && TenantId is not null)
            throw new EtsApplicationException("unsafe_configuration", "Bearer authentication derives ETS scope from authenticated claims.");
        if (Timeout <= TimeSpan.Zero || Timeout > TimeSpan.FromSeconds(60))
            throw new EtsApplicationException("unsafe_configuration", "Timeout must be greater than zero and at most 60 seconds.");
        if (BaseUri.Scheme == "http" && (!AllowInsecureLoopbackHttp || !BaseUri.IsLoopback))
            throw new EtsApplicationException("unsafe_configuration", "HTTP is allowed only for an explicitly enabled loopback ETS Dev endpoint.");
    }
}
