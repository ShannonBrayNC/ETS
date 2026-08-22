[CmdletBinding()]
param(
    [switch]$Apply
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$delegateScript = Join-Path $PSScriptRoot 'ensure-fleet-entra-application.ps1'
if (-not (Test-Path -LiteralPath $delegateScript -PathType Leaf)) {
    throw 'Governed Fleet Entra bootstrap script is missing.'
}

if (-not (Get-Module -ListAvailable -Name 'Microsoft.Graph.Authentication')) {
    throw "Required module 'Microsoft.Graph.Authentication' is not installed."
}
Import-Module Microsoft.Graph.Authentication -ErrorAction Stop

function Connect-MgGraph {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$TenantId,

        [Parameter(Mandatory = $true)]
        [string[]]$Scopes,

        [Parameter(Mandatory = $true)]
        [ValidateSet('Process')]
        [string]$ContextScope,

        [switch]$NoWelcome
    )

    $connectParameters = @{
        TenantId = $TenantId
        Scopes = $Scopes
        ContextScope = $ContextScope
        UseDeviceAuthentication = $true
    }
    if ($NoWelcome) {
        $connectParameters['NoWelcome'] = $true
    }

    Microsoft.Graph.Authentication\Connect-MgGraph @connectParameters
}

& $delegateScript -Apply:$Apply
