using System.Text.Json;
using Ets.Evidence.Canonicalization;
using Xunit;

namespace Ets.Evidence.Tests;

public sealed class EvidenceCanonicalizerTests
{
    public static IEnumerable<object[]> Vectors()
    {
        yield return new object[] { "minimal" };
        yield return new object[] { "software-release" };
        yield return new object[] { "edge-observation" };
        yield return new object[] { "correction" };
    }

    [Theory]
    [MemberData(nameof(Vectors))]
    public void Shared_vectors_match_python_contract(string name)
    {
        string root = FindRepositoryRoot();
        string examplePath = Path.Combine(root, "schemas", "evidence-object", "v1", "examples", $"{name}.json");
        string vectorPath = Path.Combine(root, "schemas", "evidence-object", "v1", "vectors", $"{name}.sha256.json");

        string example = File.ReadAllText(examplePath);
        using JsonDocument vector = JsonDocument.Parse(File.ReadAllText(vectorPath));

        int expectedLength = vector.RootElement.GetProperty("canonical_byte_length").GetInt32();
        string expectedHash = vector.RootElement.GetProperty("expected_hash").GetString()
            ?? throw new InvalidDataException("Vector expected_hash is required.");
        string profile = vector.RootElement.GetProperty("profile").GetString()
            ?? throw new InvalidDataException("Vector profile is required.");

        byte[] canonical = EvidenceCanonicalizer.Canonicalize(example);

        Assert.Equal(EvidenceCanonicalizer.HashProfile, profile);
        Assert.Equal(expectedLength, canonical.Length);
        Assert.Equal(expectedHash, EvidenceCanonicalizer.Sha256(example));
    }

    private static string FindRepositoryRoot()
    {
        DirectoryInfo? directory = new(AppContext.BaseDirectory);
        while (directory is not null)
        {
            if (Directory.Exists(Path.Combine(directory.FullName, "schemas", "evidence-object", "v1")))
            {
                return directory.FullName;
            }

            directory = directory.Parent;
        }

        throw new DirectoryNotFoundException("Could not locate the ETS repository root.");
    }
}
