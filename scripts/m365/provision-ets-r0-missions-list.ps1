[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)]
    [string]$SiteId,

    [string]$ListDisplayName = 'ETS R0 Missions'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Assert-Command {
    param([Parameter(Mandatory = $true)][string]$Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' is not installed or not available on PATH."
    }
}

function Invoke-GraphGet {
    param([Parameter(Mandatory = $true)][string]$Uri)

    return Invoke-MgGraphRequest -Method GET -Uri $Uri -OutputType PSObject
}

function Get-ColumnByName {
    param(
        [Parameter(Mandatory = $true)][object[]]$Columns,
        [Parameter(Mandatory = $true)][string]$Name
    )

    $matches = @($Columns | Where-Object { [string]$_.name -ceq $Name })
    if ($matches.Count -ne 1) {
        throw "Expected exactly one SharePoint column named '$Name'; found $($matches.Count)."
    }
    return $matches[0]
}

function Assert-MissionListShape {
    param(
        [Parameter(Mandatory = $true)][string]$VerifiedSiteId,
        [Parameter(Mandatory = $true)][object]$List
    )

    $columnsResponse = Invoke-GraphGet -Uri (
        "https://graph.microsoft.com/v1.0/sites/$VerifiedSiteId/lists/$($List.id)/columns?" +
        "`$select=name,required,indexed,enforceUniqueValues,text,dateTime"
    )
    $columns = @($columnsResponse.value)

    $requiredNames = @(
        'MissionId',
        'ScenarioId',
        'RequestedAction',
        'AuthorizationState',
        'AuthorizedByObjectId',
        'AuthorizedAt',
        'PolicyVersion',
        'CommandParameters',
        'Status',
        'EvidenceObjectId',
        'EvidenceBundleRef'
    )

    foreach ($name in $requiredNames) {
        [void](Get-ColumnByName -Columns $columns -Name $name)
    }

    $missionId = Get-ColumnByName -Columns $columns -Name 'MissionId'
    if (-not [bool]$missionId.required) {
        throw 'MissionId column must be required.'
    }
    if (-not [bool]$missionId.indexed) {
        throw 'MissionId column must be indexed.'
    }
    if (-not [bool]$missionId.enforceUniqueValues) {
        throw 'MissionId column must enforce unique values.'
    }
    if ($null -eq $missionId.text -or [int]$missionId.text.maxLength -ne 36) {
        throw 'MissionId column must be a 36-character text field.'
    }

    [pscustomobject]@{
        siteId = $VerifiedSiteId
        listId = [string]$List.id
        displayName = [string]$List.displayName
        missionIdRequired = [bool]$missionId.required
        missionIdIndexed = [bool]$missionId.indexed
        missionIdUnique = [bool]$missionId.enforceUniqueValues
        graphMutationPerformed = $false
        contractId = 'lantern.demo.agent365-r0.mission.v1'
        scenarioId = 'agent365-r0-forward-stop-v1'
    }
}

Assert-Command -Name 'Connect-MgGraph'
Assert-Command -Name 'Disconnect-MgGraph'
Assert-Command -Name 'Get-MgContext'
Assert-Command -Name 'Invoke-MgGraphRequest'

$requiredScopes = @('Sites.Manage.All')
$connected = $false
try {
    Connect-MgGraph -Scopes $requiredScopes -ContextScope Process -NoWelcome
    $connected = $true

    $context = Get-MgContext
    $effectiveScopes = @($context.Scopes)
    $missingScopes = @($requiredScopes | Where-Object { $effectiveScopes -notcontains $_ })
    if ($missingScopes.Count -gt 0) {
        throw ('Microsoft Graph token is missing required delegated scopes: ' + ($missingScopes -join ', '))
    }

    $site = Invoke-GraphGet -Uri (
        "https://graph.microsoft.com/v1.0/sites/$SiteId?`$select=id,webUrl"
    )
    if (-not $site.id -or [string]$site.id -cne $SiteId) {
        throw 'Resolved SharePoint site ID does not match the requested site.'
    }

    $listsResponse = Invoke-GraphGet -Uri (
        "https://graph.microsoft.com/v1.0/sites/$SiteId/lists?`$select=id,displayName"
    )
    $existing = @($listsResponse.value | Where-Object {
        [string]$_.displayName -ceq $ListDisplayName
    })
    if ($existing.Count -gt 1) {
        throw "Multiple SharePoint lists are named '$ListDisplayName'."
    }
    if ($existing.Count -eq 1) {
        Assert-MissionListShape -VerifiedSiteId $SiteId -List $existing[0] | ConvertTo-Json -Depth 6
        return
    }

    $columns = @(
        @{ name = 'MissionId'; required = $true; indexed = $true; enforceUniqueValues = $true; text = @{ maxLength = 36 } },
        @{ name = 'ScenarioId'; required = $true; indexed = $true; text = @{ maxLength = 128 } },
        @{ name = 'RequestedAction'; required = $true; indexed = $true; text = @{ maxLength = 128 } },
        @{ name = 'AuthorizationState'; required = $true; indexed = $true; text = @{ maxLength = 32 } },
        @{ name = 'AuthorizedByObjectId'; required = $false; indexed = $true; text = @{ maxLength = 36 } },
        @{ name = 'AuthorizedAt'; required = $false; dateTime = @{ format = 'dateTime'; displayAs = 'default' } },
        @{ name = 'PolicyVersion'; required = $true; indexed = $true; text = @{ maxLength = 256 } },
        @{ name = 'CommandParameters'; required = $true; text = @{ allowMultipleLines = $true; appendChangesToExistingText = $false; linesForEditing = 8 } },
        @{ name = 'Status'; required = $true; indexed = $true; text = @{ maxLength = 64 } },
        @{ name = 'EvidenceObjectId'; required = $false; indexed = $true; text = @{ maxLength = 255 } },
        @{ name = 'EvidenceBundleRef'; required = $false; text = @{ allowMultipleLines = $true; appendChangesToExistingText = $false; linesForEditing = 4 } }
    )

    $body = @{
        displayName = $ListDisplayName
        columns = $columns
        list = @{ template = 'genericList' }
    } | ConvertTo-Json -Depth 10

    if (-not $PSCmdlet.ShouldProcess(
        "SharePoint site $SiteId",
        "Create '$ListDisplayName' mission authorization list"
    )) {
        return
    }

    $created = Invoke-MgGraphRequest `
        -Method POST `
        -Uri "https://graph.microsoft.com/v1.0/sites/$SiteId/lists" `
        -Body $body `
        -ContentType 'application/json' `
        -OutputType PSObject

    $result = Assert-MissionListShape -VerifiedSiteId $SiteId -List $created
    $result.graphMutationPerformed = $true
    $result | ConvertTo-Json -Depth 6
}
finally {
    if ($connected) {
        Disconnect-MgGraph | Out-Null
    }
}
