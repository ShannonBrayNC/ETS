namespace Ets.Application;

public sealed class EtsApplicationException : Exception
{
    public EtsApplicationException(
        string code,
        string message,
        int? statusCode = null,
        string? apiCode = null,
        string? correlationId = null)
        : base(message)
    {
        Code = code;
        StatusCode = statusCode;
        ApiCode = apiCode;
        CorrelationId = correlationId;
    }

    public string Code { get; }
    public int? StatusCode { get; }
    public string? ApiCode { get; }
    public string? CorrelationId { get; }

    internal static string NormalizeCode(string? apiCode, int statusCode) =>
        apiCode switch
        {
            "ETS_AUTH_REQUIRED" => "authentication_failed",
            "ETS_AUTH_FORBIDDEN" => "authorization_failed",
            "ETS_EVENT_NOT_FOUND" => "not_found",
            "ETS_EVENT_DUPLICATE" => "conflict",
            "ETS_VALIDATION_ERROR" => "validation_failed",
            "ETS_REQUEST_TOO_LARGE" => "request_too_large",
            "ETS_STORAGE_VALIDATION_ERROR" => "server_error",
            _ when statusCode == 401 => "authentication_failed",
            _ when statusCode == 403 => "authorization_failed",
            _ when statusCode == 404 => "not_found",
            _ when statusCode == 409 => "conflict",
            _ when statusCode == 413 => "request_too_large",
            _ when statusCode is 400 or 422 => "validation_failed",
            _ when statusCode >= 500 => "server_error",
            _ => "unknown_error",
        };
}
