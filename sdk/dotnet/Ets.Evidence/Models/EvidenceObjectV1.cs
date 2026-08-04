using System.Text.Json.Serialization;

namespace Ets.Evidence.Models;

/// <summary>Identifies an Evidence Object and its schema-qualified version.</summary>
/// <param name="EvidenceId">The stable identifier for the evidence object.</param>
/// <param name="Version">The positive version number of this evidence object.</param>
/// <param name="Namespace">The namespace that governs the evidence identifier.</param>
/// <param name="EvidenceType">The domain-specific type of evidence represented.</param>
/// <param name="SchemaVersion">The Evidence Object schema version.</param>
public sealed record EvidenceIdentityV1(
    [property: JsonPropertyName("evidence_id")] string EvidenceId,
    [property: JsonPropertyName("version")] int Version,
    [property: JsonPropertyName("namespace")] string Namespace,
    [property: JsonPropertyName("evidence_type")] string EvidenceType,
    [property: JsonPropertyName("schema_version")] string SchemaVersion = "ets.evidence-object.v1");

/// <summary>Represents one structured claim carried by an Evidence Object.</summary>
/// <param name="ClaimId">The identifier of the claim within the evidence object.</param>
/// <param name="Subject">The entity or concept about which the claim is made.</param>
/// <param name="Predicate">The relationship or assertion applied to the subject.</param>
/// <param name="Object">An optional referenced object of the assertion.</param>
/// <param name="Value">An optional literal value asserted by the claim.</param>
/// <param name="Confidence">An optional confidence value supplied by the source.</param>
/// <param name="SourceRef">An optional reference to supporting provenance.</param>
public sealed record ClaimV1(
    [property: JsonPropertyName("claim_id")] string ClaimId,
    [property: JsonPropertyName("subject")] string Subject,
    [property: JsonPropertyName("predicate")] string Predicate,
    [property: JsonPropertyName("object")] string? Object = null,
    [property: JsonPropertyName("value")] object? Value = null,
    [property: JsonPropertyName("confidence")] double? Confidence = null,
    [property: JsonPropertyName("source_ref")] string? SourceRef = null);

/// <summary>Defines the portable Evidence Object v1 transport model.</summary>
/// <param name="Identity">The stable identity and schema-qualified version.</param>
/// <param name="CreatedAt">The UTC timestamp at which the evidence object was created.</param>
/// <param name="Claims">The ordered claims included in the object's canonical representation.</param>
/// <param name="SchemaId">The canonical identifier of the Evidence Object schema.</param>
/// <param name="Extensions">Optional namespaced extension values included by the producer.</param>
public sealed record EvidenceObjectV1(
    [property: JsonPropertyName("identity")] EvidenceIdentityV1 Identity,
    [property: JsonPropertyName("created_at")] DateTimeOffset CreatedAt,
    [property: JsonPropertyName("claims")] IReadOnlyList<ClaimV1> Claims,
    [property: JsonPropertyName("schema_id")] string SchemaId =
        "https://lanternprotocol.org/schemas/ets/evidence-object/v1",
    [property: JsonPropertyName("extensions")] IReadOnlyDictionary<string, object?>? Extensions = null);
