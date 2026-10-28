using System.Net;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Ets.Application;

return await Example.RunAsync(args);

internal static class Example
{
    private const int Limit = 4 * 1024 * 1024;

    public static async Task<int> RunAsync(string[] args)
    {
        try
        {
            bool smoke = args.Length == 3 && args[0] == "--smoke";
            if (!smoke && !(args.Length == 2 && args[0] == "--live"))
                throw new ArgumentException("Use --smoke <signed-fixture.json> <new-output.json> or --live <new-output.json>");
            string output = smoke ? args[2] : args[1];
            if (File.Exists(output) || Directory.Exists(output)) throw new IOException("Choose a new output path before capture");
            using var deadline = new CancellationTokenSource(TimeSpan.FromSeconds(30));
            ConsoleCancelEventHandler cancel = (_, e) => { e.Cancel = true; deadline.Cancel(); };
            Console.CancelKeyPress += cancel;
            try
            {
                using JsonDocument? fixture = smoke ? ReadFixture(args[1]) : null;
                var mock = fixture is null ? null : new SyntheticHandler(fixture.RootElement);
                using HttpMessageHandler handler = mock is not null ? mock : new HttpClientHandler { AllowAutoRedirect = false };
                using var http = new HttpClient(handler);
                var options = smoke
                    ? new EtsClientOptions { BaseUri = new Uri("https://ets.example/"), BearerToken = "synthetic-not-a-secret" }
                    : LiveOptions();
                // Match SDK BaseUri; injected HttpClient otherwise may retain a different origin.
                http.BaseAddress = options.BaseUri;
                using var client = new EtsClient(options, http);
                JsonElement evidence = fixture is null ? LiveEvent() : fixture.RootElement.GetProperty("event");
                _ = await client.HealthAsync(deadline.Token);
                _ = await client.CheckCompatibilityAsync(deadline.Token);
                EventCommitReceipt receipt = await client.CaptureAsync(evidence, "sdk-example-correlation", deadline.Token);
                Require(receipt.CommitmentState == "committed_local", "Unexpected receipt state");
                using JsonDocument bundle = await client.GetBundleAsync(receipt.EventId, deadline.Token);
                byte[] bytes = Encoding.UTF8.GetBytes(bundle.RootElement.GetRawText() + "\n");
                if (bytes.Length > Limit) throw new InvalidDataException("Export exceeds sample limit");
                using (var file = new FileStream(output, FileMode.CreateNew, FileAccess.Write, FileShare.None))
                    await file.WriteAsync(bytes, deadline.Token);
                if (smoke)
                {
                    Require(mock!.CaptureCount == 1, "Capture was unexpectedly repeated");
                    await CheckNegativeResponsesAsync(deadline.Token);
                }
                Console.WriteLine($"mode={(smoke ? "simulated_transport" : "live_capture")}");
                Console.WriteLine("commitment_state=committed_local; independent_verification=not_performed");
                Console.WriteLine($"bundle_saved={output}");
                if (smoke) Console.WriteLine("synthetic_success_and_error_checks=passed");
                return 0;
            }
            finally { Console.CancelKeyPress -= cancel; }
        }
        catch (EtsApplicationException ex)
        {
            Console.Error.WriteLine($"ETS failed: code={ex.Code}; http={ex.StatusCode?.ToString() ?? "none"}");
        }
        catch (Exception ex) when (ex is ArgumentException or IOException or JsonException or OperationCanceledException or InvalidOperationException)
        {
            // Do not dump credentials, arbitrary server messages or response bodies.
            Console.Error.WriteLine($"Sample failed: {ex.GetType().Name}; inspect configuration locally");
        }
        return 1;
    }

    private static JsonDocument ReadFixture(string path)
    {
        if (new FileInfo(path).Length > Limit) throw new InvalidDataException("Fixture too large");
        return JsonDocument.Parse(File.ReadAllBytes(path));
    }

    private static string Required(string name) =>
        Environment.GetEnvironmentVariable(name) is string value && !string.IsNullOrWhiteSpace(value)
            ? value : throw new ArgumentException($"Set {name} before live capture");

    private static EtsClientOptions LiveOptions()
    {
        var uri = new Uri(Required("ETS_BASE_URL"), UriKind.Absolute);
        if (uri.UserInfo.Length > 0 || uri.Query.Length > 0 || uri.Fragment.Length > 0 || !uri.AbsolutePath.EndsWith('/'))
            throw new ArgumentException("Endpoint must end with / and contain no embedded credentials, query or fragment");
        bool local = Environment.GetEnvironmentVariable("ETS_ALLOW_LOCAL_DEV") == "1";
        if (local ? uri.Scheme != "http" || !uri.IsLoopback : uri.Scheme != "https")
            throw new ArgumentException("Use HTTPS, or explicit HTTP loopback development mode");
        string? token = Environment.GetEnvironmentVariable("ETS_BEARER_TOKEN");
        string? key = Environment.GetEnvironmentVariable("ETS_API_KEY");
        if (token is not null && key is not null) throw new ArgumentException("Choose one authentication mode");
        if (!local && string.IsNullOrWhiteSpace(token) && string.IsNullOrWhiteSpace(key))
            throw new ArgumentException("Provide one nonempty credential");
        if (local && token is not null) throw new ArgumentException("Local example uses development headers, not bearer scope");
        return new EtsClientOptions
        {
            BaseUri = uri, ApiKey = key, BearerToken = token, Timeout = TimeSpan.FromSeconds(10),
            AllowInsecureLoopbackHttp = local,
            TenantId = local ? Required("ETS_TENANT_ID") : null,
            WorkspaceId = local ? Required("ETS_WORKSPACE_ID") : null,
        };
    }

    private static JsonElement LiveEvent() => JsonSerializer.SerializeToElement(new
    {
        schema_version = "ets.event.v1",
        event_id = Required("ETS_EVENT_ID"), // Persist before capture; do not regenerate after an uncertain write.
        tenant_id = Required("ETS_TENANT_ID"), workspace_id = Required("ETS_WORKSPACE_ID"),
        evidence_id = $"synthetic:{Required("ETS_EVENT_ID")}",
        event_type = "sdk.synthetic.observation", subject_ref = "synthetic:integration-example",
        content_hash = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes("Synthetic SDK integration example\n"))).ToLowerInvariant(),
        content_hash_alg = "sha256", metadata = new { synthetic = true, description = "Example observation, not a real-world claim" },
        created_at_utc = Required("ETS_EVENT_TIME_UTC"), source_system = "ets-sdk-example",
    });

    private static async Task CheckNegativeResponsesAsync(CancellationToken token)
    {
        using var http = new HttpClient(new FixedHandler(HttpStatusCode.Forbidden,
            "{\"error\":{\"code\":\"ETS_AUTH_FORBIDDEN\",\"message\":\"synthetic denial\"}}"));
        using var client = new EtsClient(new EtsClientOptions { BaseUri = new Uri("https://ets.example/") }, http);
        try { _ = await client.HealthAsync(token); throw new InvalidOperationException("Expected forbidden response"); }
        catch (EtsApplicationException ex) when (ex.Code == "authorization_failed") { }
        using var malformedHttp = new HttpClient(new FixedHandler(HttpStatusCode.OK, "not-json"));
        using var malformed = new EtsClient(new EtsClientOptions { BaseUri = new Uri("https://ets.example/") }, malformedHttp);
        try { _ = await malformed.HealthAsync(token); throw new InvalidOperationException("Expected malformed response"); }
        catch (JsonException) { }
    }

    private static void Require(bool condition, string message)
    {
        if (!condition) throw new InvalidOperationException(message);
    }

    private sealed class FixedHandler(HttpStatusCode status, string body) : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken token)
        {
            token.ThrowIfCancellationRequested();
            return Task.FromResult(new HttpResponseMessage(status) { Content = new StringContent(body, Encoding.UTF8, "application/json") });
        }
    }

    private sealed class SyntheticHandler(JsonElement fixture) : HttpMessageHandler
    {
        public int CaptureCount { get; private set; }
        protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken token)
        {
            token.ThrowIfCancellationRequested();
            Require(request.Headers.GetValues("X-ETS-SDK-Contract").Single() == "ets.application.sdk.v1", "Missing SDK contract");
            Require(request.Headers.Authorization?.ToString() == "Bearer synthetic-not-a-secret", "Missing synthetic bearer");
            Require(!request.Headers.Contains("X-ETS-Tenant"), "Bearer scope headers must be absent");
            string eventId = fixture.GetProperty("event").GetProperty("event_id").GetString()!;
            object value;
            HttpStatusCode status = HttpStatusCode.OK;
            switch ($"{request.Method} {request.RequestUri!.AbsolutePath}")
            {
                case "GET /health": value = new { status = "ok", version = "0.1.0a1" }; break;
                case "GET /version": value = new { name = "ETS", version = "0.1.0a1", api_version = "v1" }; break;
                case "POST /api/v1/events":
                    using (JsonDocument submitted = JsonDocument.Parse(await request.Content!.ReadAsStringAsync(token)))
                        Require(submitted.RootElement.GetProperty("event_id").GetString() == eventId, "Wrong event submitted");
                    Require(request.Headers.GetValues("X-Correlation-ID").Single() == "sdk-example-correlation", "Missing correlation");
                    CaptureCount++;
                    value = new { event_id = eventId, log_index = fixture.GetProperty("inclusion_proof").GetProperty("leaf_index").GetInt64(),
                        event_hash = fixture.GetProperty("event_hash").GetString(), tree_head = fixture.GetProperty("tree_head"),
                        inclusion_proof_url = $"/api/v1/proofs/inclusion/{eventId}" };
                    status = HttpStatusCode.Created;
                    break;
                default:
                    Require(request.Method == HttpMethod.Get && request.RequestUri.AbsolutePath == $"/api/v1/bundles/{Uri.EscapeDataString(eventId)}", "Unexpected mock request");
                    value = fixture;
                    break;
            }
            return new HttpResponseMessage(status) { Content = new StringContent(JsonSerializer.Serialize(value), Encoding.UTF8, "application/json") };
        }
    }
}
