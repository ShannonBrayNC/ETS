[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[a-z0-9][a-z0-9-]{5,31}$')]
    [string]$Marker,

    [string]$DriveId = '',

    [Parameter(Mandatory = $true)]
    [ValidateRange(1, 10)]
    [int]$Revision,

    [string]$SharePointHostname = 'echomediaai.sharepoint.com',

    [ValidatePattern('^/(sites|teams)/[^/]+')]
    [string]$SitePath = '/sites/ETS',

    [string]$ExpectedVerifiedDomain = 'echomedia.ai',

    [string]$ExpectedOperatorAccount = 'shannon.bray@echomedia.ai',

    [switch]$DispatchQualification
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Assert-Command {
    param([Parameter(Mandatory = $true)][string]$Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' is not installed or available on PATH."
    }
}

function Invoke-GraphGet {
    param([Parameter(Mandatory = $true)][string]$Uri)

    return Invoke-MgGraphRequest -Method GET -Uri $Uri -OutputType PSObject
}

Assert-Command -Name 'az'
Assert-Command -Name 'Connect-MgGraph'
Assert-Command -Name 'Disconnect-MgGraph'
Assert-Command -Name 'Get-MgContext'
Assert-Command -Name 'Invoke-MgGraphRequest'
if ($DispatchQualification) {
    Assert-Command -Name 'gh'
}

if ($SharePointHostname -notmatch '\.sharepoint\.com$') {
    throw 'SharePointHostname must end in .sharepoint.com.'
}
if ([string]::IsNullOrWhiteSpace($ExpectedOperatorAccount)) {
    throw 'ExpectedOperatorAccount is required.'
}

$azureAccount = az account show --output json | ConvertFrom-Json
if (-not $azureAccount.tenantId) {
    throw 'Azure CLI is not signed in to the EchoMedia Entra tenant.'
}

$fileName = "ets-live-qualification-$Marker.txt"
$content = @"
ETS live SharePoint qualification
marker=$Marker
revision=$Revision
synthetic=true
customer_content=false
"@
$contentBytes = [System.Text.Encoding]::UTF8.GetBytes($content)
$contentHash = [Convert]::ToHexString(
    [System.Security.Cryptography.SHA256]::HashData($contentBytes)
).ToLowerInvariant()
$tempPath = [System.IO.Path]::GetTempFileName()
[System.IO.File]::WriteAllBytes($tempPath, $contentBytes)

$connected = $false
try {
    Connect-MgGraph `
        -TenantId $azureAccount.tenantId `
        -Scopes 'Sites.ReadWrite.All' `
        -ContextScope Process `
        -NoWelcome
    $connected = $true

    $context = Get-MgContext
    if (-not $context.TenantId -or $context.TenantId -ne $azureAccount.tenantId) {
        throw 'Microsoft Graph tenant does not match the active Azure subscription tenant.'
    }
    if (-not $context.Account -or $context.Account -ine $ExpectedOperatorAccount) {
        throw (
            "Microsoft Graph operator '$($context.Account)' does not match the required " +
            "EchoMedia account '$ExpectedOperatorAccount'."
        )
    }

    $organization = Invoke-GraphGet -Uri (
        "https://graph.microsoft.com/v1.0/organization?`$select=id,verifiedDomains"
    )
    $organizations = @($organization.value)
    if ($organizations.Count -ne 1) {
        throw 'Expected exactly one Microsoft Entra organization.'
    }
    $verified = @($organizations[0].verifiedDomains | Where-Object {
        $_.name -ieq $ExpectedVerifiedDomain
    })
    if ($verified.Count -ne 1) {
        throw "Authenticated tenant does not contain verified domain '$ExpectedVerifiedDomain'."
    }

    $site = Invoke-GraphGet -Uri (
        "https://graph.microsoft.com/v1.0/sites/${SharePointHostname}:${SitePath}?" +
        "`$select=id,displayName,webUrl"
    )
    if (-not $site.id -or -not $site.webUrl) {
        throw 'The approved EchoMedia SharePoint site could not be resolved.'
    }
    $siteUri = [uri]$site.webUrl
    if ($siteUri.Host -ine $SharePointHostname) {
        throw 'Resolved SharePoint site hostname differs from the approved hostname.'
    }

    $encodedSiteId = [uri]::EscapeDataString([string]$site.id)
    $drives = Invoke-GraphGet -Uri (
        "https://graph.microsoft.com/v1.0/sites/$encodedSiteId/drives?`$select=id,name,webUrl"
    )
    if ([string]::IsNullOrWhiteSpace($DriveId)) {
        $approvedDrive = @($drives.value | Where-Object { $_.name -eq 'Documents' })
        if ($approvedDrive.Count -ne 1) {
            throw 'The ETS Documents library could not be resolved uniquely.'
        }
    }
    else {
        $approvedDrive = @($drives.value | Where-Object { $_.id -eq $DriveId })
        if ($approvedDrive.Count -ne 1) {
            throw 'DriveId does not resolve uniquely inside the approved ETS SharePoint site.'
        }
        if ($approvedDrive[0].name -ne 'Documents') {
            throw 'The approved drive is not the ETS Documents library.'
        }
    }
    $resolvedDriveId = [string]$approvedDrive[0].id
    if ([string]::IsNullOrWhiteSpace($resolvedDriveId)) {
        throw 'The approved ETS Documents library did not expose a drive identifier.'
    }

    $encodedDrive = [uri]::EscapeDataString($resolvedDriveId)
    $encodedName = [uri]::EscapeDataString($fileName)
    $uploadUri = (
        "https://graph.microsoft.com/v1.0/drives/$encodedDrive/root:/" +
        "$encodedName`:/content"
    )
    $uploaded = Invoke-MgGraphRequest `
        -Method PUT `
        -Uri $uploadUri `
        -InputFilePath $tempPath `
        -ContentType 'text/plain' `
        -OutputType PSObject

    if (-not $uploaded.id -or $uploaded.name -ne $fileName -or -not $uploaded.eTag) {
        throw 'Graph did not return the expected qualification file metadata after upload.'
    }

    $metadata = Invoke-GraphGet -Uri (
        "https://graph.microsoft.com/v1.0/drives/$encodedDrive/root:/${encodedName}?" +
        "`$select=id,name,eTag,cTag,size,lastModifiedDateTime,file"
    )
    if ($metadata.name -ne $fileName -or $metadata.eTag -ne $uploaded.eTag) {
        throw 'Post-upload SharePoint metadata did not converge to the uploaded revision.'
    }
    if ($null -eq $metadata.file) {
        throw 'Qualification object is not a file.'
    }

    [pscustomobject]@{
        stage = 'qualification_document_ready'
        marker = $Marker
        fileName = $fileName
        revision = $Revision
        contentSha256 = $contentHash
        operatorAccountVerified = $true
        documentsDriveResolved = $true
        sharePointMetadataVerified = $true
        sourceMutationReady = $true
        rawCustomerContentUsed = $false
        customerIdentifiersRetained = $false
        reusableCredentialRetained = $false
        publicEvidenceSafe = $true
    } | ConvertTo-Json -Depth 4
}
finally {
    if ($connected) {
        Disconnect-MgGraph | Out-Null
    }
    Remove-Item -LiteralPath $tempPath -Force -ErrorAction SilentlyContinue
}

if ($DispatchQualification) {
    gh workflow run live-sharepoint-source-to-proof.yml `
        -R ShannonBrayNC/ETS `
        --ref main `
        -f "marker=$Marker" `
        -f "expected_observations=$Revision"
    if ($LASTEXITCODE -ne 0) {
        throw 'GitHub workflow dispatch failed.'
    }
}
