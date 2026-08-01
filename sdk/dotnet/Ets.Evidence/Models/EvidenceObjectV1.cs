using System.Text.Json.Serialization;

namespace Ets.Evidence.Models;

public sealed record EvidenceIdentityV1(
    [property: JsonPropertyName("evidence_id")] string EvidenceId,
    [property: JsonPropertyName("version")] int Version,
    [property: JsonPropertyName("namespace")] string Namespace,
    [property: JsonPropertyName("evidence_type")] string EvidenceType,
    [property: JsonPropertyName("schema_version")] string SchemaVersion = "ets.evidence-object.v1");

public sealed record ClaimV1(
    [property: JsonPropertyName("claim_id")] string ClaimId,
    [property: JsonPropertyName("subject")] string Subject,
    [property: JsonPropertyName("predicate")] string Predicate,
    [property: JsonPropertyName("object")] string? Object = null,
    [property: JsonPropertyName("value")] object? Value = null,
    [property: JsonPropertyName("confidence")] double? Confidence = null,
    [property: JsonPropertyName("source_ref")] string? SourceRef = null);

public sealed record EvidenceObjectV1(
    [property: JsonPropertyName("identity")] EvidenceIdentityV1 Identity,
    [property: JsonPropertyName("created_at")] DateTimeOffset CreatedAt,
    [property: JsonPropertyName("claims")] IReadOnlyList<ClaimV1> Claims,
    [property: JsonPropertyName("schema_id")] string SchemaId =
        "https://lanternprotocol.org/schemas/ets/evidence-object/v1",
    [property: JsonPropertyName("extensions")] IReadOnlyDictionary<string, object?>? Extensions = null);
