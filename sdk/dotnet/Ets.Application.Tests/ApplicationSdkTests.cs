using System.Net;
using System.Text;
using System.Text.Json;
using Ets.Application;
using Xunit;

namespace Ets.Application.Tests;

public sealed class ApplicationSdkTests
{
    [Fact]
    public async Task Capture_returns_local_commit_receipt_and_sends_sdk_contract()
    {
        var handler = new StubHandler(request =>
        {
            Assert.Equal("ets.application.sdk.v1", request.Headers.GetValues("X-ETS-SDK-Contract").Single());
            Assert.Equal("dev-key", request.Headers.GetValues("X-ETS-API-Key").Single());
            Assert.Equal("tenant-dev", request.Headers.GetValues("X-ETS-Tenant").Single());
            const string body = """
            {
              "event_id":"evt-dotnet-1","log_index":0,
              "event_hash":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
              "tree_head":{"tree_size":1,"root_hash":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","created_at_utc":"2026-09-25T16:00:00Z","log_id":"ets-sdk-dev","signature_alg":null,"signature":null,"public_key_id":null},
              "inclusion_proof_url":"/api/v1/proofs/inclusion/evt-dotnet-1"
            }
            """;
            return new HttpResponseMessage(HttpStatusCode.Created) { Content = new StringContent(body, Encoding.UTF8, "application/json") };
        });

        using var http = new HttpClient(handler) { BaseAddress = new Uri("https://ets.example/") };
        using var client = new EtsClient(new EtsClientOptions
        {
            BaseUri = new Uri("https://ets.example/"),
            ApiKey = "dev-key",
            TenantId = "tenant-dev",
            WorkspaceId = "default",
        }, http);

        EventCommitReceipt receipt = await client.CaptureAsync(new { event_id = "evt-dotnet-1" });

        Assert.Equal("committed_local", receipt.CommitmentState);
        Assert.Equal("ets.sdk.event_commit_receipt.v1", receipt.SchemaVersion);
        Assert.Equal("evt-dotnet-1", receipt.EventId);
    }

    [Fact]
    public void Bearer_authentication_rejects_caller_controlled_scope_headers()
    {
        EtsApplicationException error = Assert.Throws<EtsApplicationException>(() =>
            new EtsClient(new EtsClientOptions
            {
                BaseUri = new Uri("https://ets.example/"),
                BearerToken = "token",
                TenantId = "tenant",
                WorkspaceId = "workspace",
            }));
        Assert.Equal("unsafe_configuration", error.Code);
    }

    [Theory]
    [InlineData("canonicalization/basic.json")]
    [InlineData("event-hashing/basic.json")]
    public void Application_sdk_vectors_match_python_reference(string relativePath)
    {
        string root = FindRepositoryRoot();
        using JsonDocument vector = JsonDocument.Parse(File.ReadAllText(Path.Combine(root, "conformance", "sdk", "v1", relativePath)));
        JsonElement input = vector.RootElement.TryGetProperty("input", out JsonElement canonicalInput)
            ? canonicalInput
            : vector.RootElement.GetProperty("hashable_payload");
        string expectedCanonical = vector.RootElement.GetProperty("canonical_utf8").GetString()
            ?? throw new InvalidDataException("canonical_utf8 is required");
        string expectedHash = vector.RootElement.GetProperty("sha256").GetString()
            ?? throw new InvalidDataException("sha256 is required");

        string inputJson = input.GetRawText();
        Assert.Equal(expectedCanonical, Encoding.UTF8.GetString(ApplicationCanonicalizer.Canonicalize(inputJson)));
        Assert.Equal(expectedHash, ApplicationCanonicalizer.Sha256(inputJson));
    }

    private static string FindRepositoryRoot()
    {
        DirectoryInfo? directory = new(AppContext.BaseDirectory);
        while (directory is not null)
        {
            if (Directory.Exists(Path.Combine(directory.FullName, "conformance", "sdk", "v1")))
                return directory.FullName;
            directory = directory.Parent;
        }
        throw new DirectoryNotFoundException("Could not locate the ETS repository root.");
    }

    private sealed class StubHandler(Func<HttpRequestMessage, HttpResponseMessage> handler) : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken) =>
            Task.FromResult(handler(request));
    }
}
