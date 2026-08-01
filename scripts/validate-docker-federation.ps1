param(
    [int]$StartupSeconds = 20
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker is not installed or not available on PATH."
}

docker compose up --build -d
try {
    Start-Sleep -Seconds $StartupSeconds
    $ports = @(8101, 8102, 8103, 8201, 8202, 8301)
    foreach ($port in $ports) {
        $health = Invoke-RestMethod "http://127.0.0.1:$port/health"
        if ($health.status -ne "ok") {
            throw "Service on port $port did not report healthy status."
        }
    }
    Write-Output "ETS Docker federation health checks passed."
}
finally {
    docker compose down
}
