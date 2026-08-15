@description('Azure region for the hosted ETS pilot resources.')
param location string = resourceGroup().location

@description('Environment label used only as a deterministic naming seed. Do not use customer data.')
@minLength(1)
param environmentName string

@description('Immutable OCI image from the approved private Azure Container Registry. Use an @sha256 digest, not a mutable tag, for qualification.')
@minLength(1)
param containerImage string

@description('Existing private Azure Container Registry name in the current subscription.')
@minLength(5)
param containerRegistryName string

@description('Resource group containing the existing private Azure Container Registry.')
@minLength(1)
param containerRegistryResourceGroup string

@description('Registry pull role: AcrPull for RBAC-only ACR, or Container Registry Repository Reader for ABAC-enabled ACR.')
@allowed([
  '7f951dda-4ed3-4680-a7ca-43fe172d538d'
  'b93aa761-3e63-49ed-ac28-beffa264f7ac'
])
param containerRegistryPullRoleDefinitionId string = '7f951dda-4ed3-4680-a7ca-43fe172d538d'

@description('Deployment-authoritative ETS log identifier.')
@minLength(1)
param logId string

@description('Production JWKS endpoint for the authorized hosted client population.')
@minLength(1)
param authJwksUrl string

@description('Expected JWT issuer for production JWKS authentication.')
@minLength(1)
param authIssuer string

@description('Expected JWT audience for production JWKS authentication.')
@minLength(1)
param authAudience string

@description('Azure Table name used for ETS event persistence.')
@minLength(3)
@maxLength(63)
param evidenceTableName string = 'ETSEvents'

@description('RSA Key Vault key name used for PS256 tree-head signing.')
@minLength(1)
param signingKeyName string = 'ets-tree-head'

@description('RSA key size used for the hosted tree-head signing key.')
@allowed([
  2048
  3072
  4096
])
param signingKeySize int = 3072

var resourceToken = uniqueString(resourceGroup().id, environmentName)
var storageAccountName = take('ets${resourceToken}', 24)
var keyVaultName = take('ets-${resourceToken}-kv', 24)
var appConfigName = take('ets-${resourceToken}-cfg', 50)
var managedEnvironmentName = take('ets-${resourceToken}-cae', 60)
var containerAppName = take('ets-${resourceToken}-api', 32)
var managedIdentityName = take('ets-${resourceToken}-identity', 128)
var registryPullIdentityName = take('ets-${resourceToken}-pull', 128)
var appInsightsName = take('ets-${resourceToken}-appi', 260)
var keyVaultCryptoUserRoleId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '12338af0-0e69-4776-bea7-57ae8d297424'
)
var storageTableDataContributorRoleId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3'
)

resource managedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: managedIdentityName
  location: location
}

resource registryPullIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: registryPullIdentityName
  location: location
}

module registryPull './modules/acr-pull-role.bicep' = {
  name: 'ets-acr-pull-${resourceToken}'
  scope: resourceGroup(containerRegistryResourceGroup)
  params: {
    registryName: containerRegistryName
    principalId: registryPullIdentity.properties.principalId
    pullRoleDefinitionId: containerRegistryPullRoleDefinitionId
  }
}

resource keyVault 'Microsoft.KeyVault/vaults@2025-05-01' = {
  name: keyVaultName
  location: location
  properties: {
    tenantId: subscription().tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    enableRbacAuthorization: true
    enabledForDeployment: false
    enabledForDiskEncryption: false
    enabledForTemplateDeployment: false
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
    enablePurgeProtection: true
    publicNetworkAccess: 'Enabled'
  }
}

resource signingKey 'Microsoft.KeyVault/vaults/keys@2025-05-01' = {
  parent: keyVault
  name: signingKeyName
  properties: {
    attributes: {
      enabled: true
      exportable: false
    }
    keyOps: [
      'sign'
      'verify'
    ]
    keySize: signingKeySize
    kty: 'RSA'
  }
}

resource keyVaultCryptoUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, managedIdentity.id, keyVaultCryptoUserRoleId)
  scope: keyVault
  properties: {
    roleDefinitionId: keyVaultCryptoUserRoleId
    principalId: managedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource storageAccount 'Microsoft.Storage/storageAccounts@2025-06-01' = {
  name: storageAccountName
  location: location
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    allowCrossTenantReplication: false
    allowSharedKeyAccess: false
    defaultToOAuthAuthentication: true
    minimumTlsVersion: 'TLS1_2'
    publicNetworkAccess: 'Enabled'
    supportsHttpsTrafficOnly: true
  }
}

resource tableService 'Microsoft.Storage/storageAccounts/tableServices@2025-06-01' = {
  parent: storageAccount
  name: 'default'
  properties: {}
}

resource evidenceTable 'Microsoft.Storage/storageAccounts/tableServices/tables@2025-06-01' = {
  parent: tableService
  name: evidenceTableName
  properties: {
    signedIdentifiers: []
  }
}

resource tableDataContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(evidenceTable.id, managedIdentity.id, storageTableDataContributorRoleId)
  scope: evidenceTable
  properties: {
    roleDefinitionId: storageTableDataContributorRoleId
    principalId: managedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource appConfig 'Microsoft.AppConfiguration/configurationStores@2024-05-01' = {
  name: appConfigName
  location: location
  sku: {
    name: 'standard'
  }
  properties: {
    disableLocalAuth: true
    enablePurgeProtection: true
    publicNetworkAccess: 'Enabled'
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    DisableLocalAuth: true
  }
}

resource managedEnvironment 'Microsoft.App/managedEnvironments@2026-01-01' = {
  name: managedEnvironmentName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'azure-monitor'
    }
    publicNetworkAccess: 'Enabled'
  }
}

resource signingMode 'Microsoft.AppConfiguration/configurationStores/keyValues@2024-05-01' = {
  parent: appConfig
  name: 'ETS_SIGNING_MODE'
  properties: {
    value: 'azure_key_vault'
  }
}

resource managedIdentityEnabled 'Microsoft.AppConfiguration/configurationStores/keyValues@2024-05-01' = {
  parent: appConfig
  name: 'ETS_AZURE_MANAGED_IDENTITY_ENABLED'
  properties: {
    value: 'true'
  }
}

resource vaultUrl 'Microsoft.AppConfiguration/configurationStores/keyValues@2024-05-01' = {
  parent: appConfig
  name: 'ETS_AZURE_KEY_VAULT_URL'
  properties: {
    value: keyVault.properties.vaultUri
  }
}

resource keyName 'Microsoft.AppConfiguration/configurationStores/keyValues@2024-05-01' = {
  parent: appConfig
  name: 'ETS_AZURE_KEY_NAME'
  properties: {
    value: signingKey.name
  }
}

// ETS_AZURE_KEY_VERSION is intentionally omitted from the Container App. The hosted
// runtime resolves the current key once at startup and pins that concrete version
// into public_key_id before signing any tree head.
resource containerApp 'Microsoft.App/containerApps@2025-01-01' = {
  name: containerAppName
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentity.id}': {}
      '${registryPullIdentity.id}': {}
    }
  }
  properties: {
    environmentId: managedEnvironment.id
    configuration: {
      activeRevisionsMode: 'Single'
      identitySettings: [
        {
          identity: managedIdentity.id
          lifecycle: 'Main'
        }
        {
          identity: registryPullIdentity.id
          lifecycle: 'None'
        }
      ]
      registries: [
        {
          server: registryPull.outputs.loginServer
          identity: registryPullIdentity.id
        }
      ]
      ingress: {
        external: false
        allowInsecure: false
        targetPort: 8000
        transport: 'auto'
      }
    }
    template: {
      containers: [
        {
          name: 'ets-api'
          image: containerImage
          env: [
            {
              name: 'ETS_STORAGE_PROVIDER'
              value: 'azure_table'
            }
            {
              name: 'ETS_AZURE_TABLE_ENDPOINT'
              value: storageAccount.properties.primaryEndpoints.table
            }
            {
              name: 'ETS_AZURE_TABLE_NAME'
              value: evidenceTable.name
            }
            {
              name: 'ETS_AZURE_MANAGED_IDENTITY_ENABLED'
              value: 'true'
            }
            {
              name: 'ETS_AZURE_MANAGED_IDENTITY_CLIENT_ID'
              value: managedIdentity.properties.clientId
            }
            {
              name: 'ETS_LOG_ID'
              value: logId
            }
            {
              name: 'ETS_SIGNING_MODE'
              value: 'azure_key_vault'
            }
            {
              name: 'ETS_AZURE_KEY_VAULT_URL'
              value: keyVault.properties.vaultUri
            }
            {
              name: 'ETS_AZURE_KEY_NAME'
              value: signingKey.name
            }
            {
              name: 'ETS_AUTH_MODE'
              value: 'production_jwks'
            }
            {
              name: 'ETS_AUTH_JWKS_URL'
              value: authJwksUrl
            }
            {
              name: 'ETS_AUTH_ISSUER'
              value: authIssuer
            }
            {
              name: 'ETS_AUTH_AUDIENCE'
              value: authAudience
            }
          ]
          probes: [
            {
              type: 'Startup'
              httpGet: {
                path: '/version'
                port: 8000
                scheme: 'HTTP'
              }
              initialDelaySeconds: 2
              periodSeconds: 5
              timeoutSeconds: 2
              failureThreshold: 10
              successThreshold: 1
            }
            {
              type: 'Liveness'
              httpGet: {
                path: '/health'
                port: 8000
                scheme: 'HTTP'
              }
              initialDelaySeconds: 5
              periodSeconds: 15
              timeoutSeconds: 2
              failureThreshold: 3
              successThreshold: 1
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/ready'
                port: 8000
                scheme: 'HTTP'
              }
              initialDelaySeconds: 5
              periodSeconds: 10
              timeoutSeconds: 3
              failureThreshold: 3
              successThreshold: 1
            }
          ]
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 1
      }
    }
  }
  dependsOn: [
    keyVaultCryptoUser
    tableDataContributor
  ]
}

output managedIdentityResourceId string = managedIdentity.id
output registryPullIdentityResourceId string = registryPullIdentity.id
output containerRegistryServer string = registryPull.outputs.loginServer
output appConfigurationEndpoint string = appConfig.properties.endpoint
output keyVaultUri string = keyVault.properties.vaultUri
output applicationInsightsName string = appInsights.name
output storageAccountName string = storageAccount.name
output evidenceTableResourceId string = evidenceTable.id
output containerAppName string = containerApp.name
output internalIngressFqdn string = containerApp.properties.configuration.ingress.fqdn
