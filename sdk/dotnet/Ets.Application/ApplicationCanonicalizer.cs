using System.Security.Cryptography;
using System.Text;
using System.Text.Encodings.Web;
using System.Text.Json;

namespace Ets.Application;

/// <summary>Canonical JSON helper for the frozen ETS Application SDK v1 conformance corpus.</summary>
public static class ApplicationCanonicalizer
{
    private static readonly JsonSerializerOptions StringOptions = new()
    {
        Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
    };

    public static byte[] Canonicalize(string json)
    {
        using JsonDocument document = JsonDocument.Parse(json);
        var builder = new StringBuilder();
        WriteCanonical(builder, document.RootElement);
        return Encoding.UTF8.GetBytes(builder.ToString());
    }

    public static string Sha256(string json) =>
        Convert.ToHexString(SHA256.HashData(Canonicalize(json))).ToLowerInvariant();

    private static void WriteCanonical(StringBuilder builder, JsonElement element)
    {
        switch (element.ValueKind)
        {
            case JsonValueKind.Object:
                builder.Append('{');
                bool firstProperty = true;
                foreach (JsonProperty property in
                    element.EnumerateObject().OrderBy(item => item.Name, StringComparer.Ordinal))
                {
                    if (!firstProperty)
                    {
                        builder.Append(',');
                    }

                    builder.Append(JsonSerializer.Serialize(property.Name, StringOptions));
                    builder.Append(':');
                    WriteCanonical(builder, property.Value);
                    firstProperty = false;
                }
                builder.Append('}');
                break;

            case JsonValueKind.Array:
                builder.Append('[');
                bool firstItem = true;
                foreach (JsonElement item in element.EnumerateArray())
                {
                    if (!firstItem)
                    {
                        builder.Append(',');
                    }

                    WriteCanonical(builder, item);
                    firstItem = false;
                }
                builder.Append(']');
                break;

            case JsonValueKind.String:
                builder.Append(JsonSerializer.Serialize(element.GetString(), StringOptions));
                break;

            case JsonValueKind.Number:
                builder.Append(element.GetRawText());
                break;

            case JsonValueKind.True:
                builder.Append("true");
                break;

            case JsonValueKind.False:
                builder.Append("false");
                break;

            case JsonValueKind.Null:
                builder.Append("null");
                break;

            default:
                throw new JsonException($"Unsupported JSON value kind: {element.ValueKind}");
        }
    }
}
