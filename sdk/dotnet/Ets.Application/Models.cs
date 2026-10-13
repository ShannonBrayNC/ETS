using System.Text.Json.Serialization;

namespace Ets.Application;

public static class EtsSdkContracts
{
    public const string ApplicationSdk = "ets.application.sdk.v1";
    public const string ApiVersion = "v1";
}

public sealed record ServiceVersion(
    [property: JsonPropertyName("name")] string Name,
    [property: JsonPropertyName("version")] string Version,
    [property: JsonPropertyName("api_version")] string ApiVersion);

public sealed record ServiceHealth(
    [property: JsonPropertyName("status")] string Status,
    [property: JsonPropertyName("version")] string Version);

public sealed record TreeHead(
    [property: JsonPropertyName("tree_size")] long TreeSize,
    [property: JsonPropertyName("root_hash")] string RootHash,
    [property: JsonPropertyName("created_at_utc")] DateTimeOffset CreatedAtUtc,
    [property: JsonPropertyName("log_id")] string LogId,
    [property: JsonPropertyName("signature_alg")] string? SignatureAlg,
    [property: JsonPropertyName("signature")] string? Signature,
    [property: JsonPropertyName("public_key_id")] string? PublicKeyId);

public sealed record EventCommitReceipt(
    string EventId,
    long LogIndex,
    string EventHash,
    TreeHead TreeHead,
    string InclusionProofUrl)
{
    public string SchemaVersion => "ets.sdk.event_commit_receipt.v1";
    public string CommitmentState => "committed_local";
}

internal sealed record EventAppendWireResponse(
    [property: JsonPropertyName("event_id")] string EventId,
    [property: JsonPropertyName("log_index")] long LogIndex,
    [property: JsonPropertyName("event_hash")] string EventHash,
    [property: JsonPropertyName("tree_head")] TreeHead TreeHead,
    [property: JsonPropertyName("inclusion_proof_url")] string InclusionProofUrl);
