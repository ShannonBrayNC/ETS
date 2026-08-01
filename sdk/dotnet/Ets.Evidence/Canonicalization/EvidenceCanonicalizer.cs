using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace Ets.Evidence.Canonicalization;

/// <summary>Provides deterministic canonical JSON serialization and hashing for Evidence Objects.</summary>
public static class EvidenceCanonicalizer
{
    /// <summary>Identifies the canonical JSON and SHA-256 hashing profile implemented here.</summary>
    public const string HashProfile = "ets.evidence-object.canonical-json.sha256.v1";

    /// <summary>Canonicalizes a JSON document into deterministic UTF-8 bytes.</summary>
    /// <param name="json">The JSON document to canonicalize.</param>
    /// <returns>The canonical UTF-8 representation.</returns>
    /// <exception cref="JsonException">Thrown when the input is invalid or contains an unsupported value.</exception>
    public static byte[] Canonicalize(string json)
    {
        using JsonDocument document = JsonDocument.Parse(json);
        using var stream = new MemoryStream();
        using (var writer = new Utf8JsonWriter(stream, new JsonWriterOptions { Indented = false }))
        {
            WriteCanonical(writer, document.RootElement);
        }

        return stream.ToArray();
    }

    /// <summary>Computes the lowercase SHA-256 digest of a canonicalized JSON document.</summary>
    /// <param name="json">The JSON document to canonicalize and hash.</param>
    /// <returns>The lowercase hexadecimal SHA-256 digest.</returns>
    /// <exception cref="JsonException">Thrown when the input cannot be canonicalized.</exception>
    public static string Sha256(string json)
    {
        byte[] digest = SHA256.HashData(Canonicalize(json));
        return Convert.ToHexString(digest).ToLowerInvariant();
    }

    private static void WriteCanonical(Utf8JsonWriter writer, JsonElement element)
    {
        switch (element.ValueKind)
        {
            case JsonValueKind.Object:
                writer.WriteStartObject();
                foreach (JsonProperty property in element.EnumerateObject().OrderBy(p => p.Name, StringComparer.Ordinal))
                {
                    writer.WritePropertyName(property.Name);
                    WriteCanonical(writer, property.Value);
                }
                writer.WriteEndObject();
                break;

            case JsonValueKind.Array:
                writer.WriteStartArray();
                foreach (JsonElement item in element.EnumerateArray())
                {
                    WriteCanonical(writer, item);
                }
                writer.WriteEndArray();
                break;

            case JsonValueKind.String:
                writer.WriteStringValue(element.GetString());
                break;

            case JsonValueKind.Number:
                writer.WriteRawValue(element.GetRawText(), skipInputValidation: false);
                break;

            case JsonValueKind.True:
                writer.WriteBooleanValue(true);
                break;

            case JsonValueKind.False:
                writer.WriteBooleanValue(false);
                break;

            case JsonValueKind.Null:
                writer.WriteNullValue();
                break;

            default:
                throw new JsonException($"Unsupported JSON value kind: {element.ValueKind}");
        }
    }
}
