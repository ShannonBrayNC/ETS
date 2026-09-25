using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;

namespace Ets.Application;

public sealed class EtsClient : IDisposable
{
    private readonly HttpClient _http;
    private readonly EtsClientOptions _options;
    private readonly bool _ownsClient;
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web);

    public EtsClient(EtsClientOptions options, HttpClient? httpClient = null)
    {
        options.Validate();
        _options = options;
        _ownsClient = httpClient is null;
        _http = httpClient ?? new HttpClient();
        _http.BaseAddress ??= options.BaseUri;
        _http.Timeout = options.Timeout;
    }

    public async Task<ServiceHealth> HealthAsync(CancellationToken cancellationToken = default) =>
        await SendAndReadAsync<ServiceHealth>(HttpMethod.Get, "health", null, cancellationToken).ConfigureAwait(false);

    public async Task<ServiceVersion> VersionAsync(CancellationToken cancellationToken = default) =>
        await SendAndReadAsync<ServiceVersion>(HttpMethod.Get, "version", null, cancellationToken).ConfigureAwait(false);

    public async Task<ServiceVersion> CheckCompatibilityAsync(CancellationToken cancellationToken = default)
    {
        ServiceVersion version = await VersionAsync(cancellationToken).ConfigureAwait(false);
        if (!string.Equals(version.ApiVersion, EtsSdkContracts.ApiVersion, StringComparison.Ordinal))
            throw new EtsApplicationException("incompatible_version", $"ETS API version '{version.ApiVersion}' is not supported.");
        return version;
    }

    public async Task<EventCommitReceipt> CaptureAsync(
        object evidenceEvent,
        string? correlationId = null,
        CancellationToken cancellationToken = default)
    {
        EventAppendWireResponse wire = await SendAndReadAsync<EventAppendWireResponse>(
            HttpMethod.Post, "api/v1/events", evidenceEvent, cancellationToken, correlationId).ConfigureAwait(false);
        return new EventCommitReceipt(wire.EventId, wire.LogIndex, wire.EventHash, wire.TreeHead, wire.InclusionProofUrl);
    }

    public Task<JsonDocument> GetEventAsync(string eventId, CancellationToken cancellationToken = default) =>
        GetJsonAsync($"api/v1/events/{Uri.EscapeDataString(RequireEventId(eventId))}", cancellationToken);

    public Task<JsonDocument> GetBundleAsync(string eventId, CancellationToken cancellationToken = default) =>
        GetJsonAsync($"api/v1/bundles/{Uri.EscapeDataString(RequireEventId(eventId))}", cancellationToken);

    public Task<JsonDocument> GetInclusionProofAsync(string eventId, CancellationToken cancellationToken = default) =>
        GetJsonAsync($"api/v1/proofs/inclusion/{Uri.EscapeDataString(RequireEventId(eventId))}", cancellationToken);

    public Task<JsonDocument> GetConsistencyProofAsync(long fromSize, long? toSize = null, CancellationToken cancellationToken = default)
    {
        if (fromSize < 0 || (toSize is not null && toSize < fromSize))
            throw new EtsApplicationException("validation_failed", "Consistency proof sizes are invalid.");
        string path = $"api/v1/proofs/consistency?from_size={fromSize}";
        if (toSize is not null) path += $"&to_size={toSize.Value}";
        return GetJsonAsync(path, cancellationToken);
    }

    public void Dispose()
    {
        if (_ownsClient) _http.Dispose();
    }

    private async Task<JsonDocument> GetJsonAsync(string path, CancellationToken cancellationToken)
    {
        using HttpRequestMessage request = CreateRequest(HttpMethod.Get, path);
        using HttpResponseMessage response = await SendAsync(request, cancellationToken).ConfigureAwait(false);
        Stream content = await response.Content.ReadAsStreamAsync(cancellationToken).ConfigureAwait(false);
        return await JsonDocument.ParseAsync(content, cancellationToken: cancellationToken).ConfigureAwait(false);
    }

    private async Task<T> SendAndReadAsync<T>(
        HttpMethod method,
        string path,
        object? body,
        CancellationToken cancellationToken,
        string? correlationId = null)
    {
        using HttpRequestMessage request = CreateRequest(method, path, correlationId);
        if (body is not null) request.Content = JsonContent.Create(body, options: JsonOptions);
        using HttpResponseMessage response = await SendAsync(request, cancellationToken).ConfigureAwait(false);
        T? value = await response.Content.ReadFromJsonAsync<T>(JsonOptions, cancellationToken).ConfigureAwait(false);
        return value ?? throw new EtsApplicationException("server_error", $"ETS API returned an empty {typeof(T).Name} response.");
    }

    private HttpRequestMessage CreateRequest(HttpMethod method, string path, string? correlationId = null)
    {
        var request = new HttpRequestMessage(method, path);
        request.Headers.Accept.Add(new MediaTypeWithQualityHeaderValue("application/json"));
        request.Headers.Add("X-ETS-SDK-Contract", EtsSdkContracts.ApplicationSdk);
        if (_options.ApiKey is not null) request.Headers.Add("X-ETS-API-Key", _options.ApiKey);
        if (_options.BearerToken is not null)
            request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", _options.BearerToken);
        else if (_options.TenantId is not null && _options.WorkspaceId is not null)
        {
            request.Headers.Add("X-ETS-Tenant", _options.TenantId);
            request.Headers.Add("X-ETS-Workspace", _options.WorkspaceId);
        }
        if (correlationId is not null) request.Headers.Add("X-Correlation-ID", correlationId);
        return request;
    }

    private async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
    {
        HttpResponseMessage response;
        try
        {
            response = await _http.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, cancellationToken).ConfigureAwait(false);
        }
        catch (HttpRequestException ex)
        {
            throw new EtsApplicationException("transport_error", $"ETS API request failed: {ex.Message}");
        }
        if (response.IsSuccessStatusCode) return response;
        await ThrowApiErrorAsync(response, cancellationToken).ConfigureAwait(false);
        throw new InvalidOperationException("unreachable");
    }

    private static async Task ThrowApiErrorAsync(HttpResponseMessage response, CancellationToken cancellationToken)
    {
        string? apiCode = null;
        string message = $"ETS API returned HTTP {(int)response.StatusCode}.";
        string? correlationId = null;
        try
        {
            using JsonDocument document = await JsonDocument.ParseAsync(
                await response.Content.ReadAsStreamAsync(cancellationToken).ConfigureAwait(false),
                cancellationToken: cancellationToken).ConfigureAwait(false);
            if (document.RootElement.TryGetProperty("error", out JsonElement error))
            {
                apiCode = error.TryGetProperty("code", out JsonElement code) ? code.GetString() : null;
                message = error.TryGetProperty("message", out JsonElement detail) ? detail.GetString() ?? message : message;
                correlationId = error.TryGetProperty("correlation_id", out JsonElement corr) ? corr.GetString() : null;
            }
        }
        catch (JsonException) { }
        throw new EtsApplicationException(
            EtsApplicationException.NormalizeCode(apiCode, (int)response.StatusCode),
            message, (int)response.StatusCode, apiCode, correlationId);
    }

    private static string RequireEventId(string eventId) =>
        !string.IsNullOrWhiteSpace(eventId)
            ? eventId
            : throw new EtsApplicationException("validation_failed", "eventId is required.");
}
