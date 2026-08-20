@description('Azure region for the hosted Gateway resources.')
param location string = resourceGroup().location

@description('Naming seed for the non-customer Gateway deployment.')
@minLength(1)
param environmentName string

@description('Existing Container Apps managed environment shared with private ETS Core.')
@minLength(1)
param managedEnvironmentName string

@description('Immutable Gateway image in the approved private ACR, pinned by sha256 digest.')
@minLength(1)
param containerImage string

@description('Existing private Azure Container Registry name.')
@minLength(5)
param containerRegistryName string

@description('Resource group containing the private Azure Container Registry.')
@minLength(1)
param containerRegistryResourceGroup string

@description('Registry pull role for the dedicated pull-only identity.')
@allowed([
  '7f951dda-4ed3-4680-a7ca-43fe172d538d'
  'b93aa761-3e63-49ed-ac28-beffa264f7ac'
])
param containerRegistryPullRoleDefinitionId string = '7f951dda-4ed3-4680-a7ca-43fe172d538d'

@description('Private HTTPS origin of the exact hosted ETS Core deployment.')
@minLength(1)
param coreBaseUrl string

@description('Fixed Entra resource scope used by Gateway managed identity for Core relay.')
@minLength(1)
param coreScope string

@description('Server-authoritative ETS tenant scope for this Gateway instance.')
@minLength(1)
param etsTenantId string

@description('Server-authoritative ETS workspace scope for this Gateway instance.')
@minLength(1)
param etsWorkspaceId string

@description('Stable Microsoft connector instance identifier.')
@minLength(1)
param connectorInstanceId string

@description('Stable authoritative Gateway source identifier.')
@minLength(1)
param sourceId string

@description('Internal principal used only for the server-owned connector-to-Gateway boundary.')
@minLength(1)
param sourcePrincipal string = 'gateway://microsoft/sharepoint'

@description('EchoMedia Microsoft Entra tenant GUID.')
@minLength(36)
@maxLength(36)
param microsoftTenantId string

@description('Approved SharePoint drive identifier.')
@minLength(1)
param sharePointDriveId string

@description('Production JWKS endpoint for Gateway management identities.')
@minLength(1)
param authJwksUrl string

@description('Expected production Gateway JWT issuer.')
@minLength(1)
param authIssuer string

@description('Expected production Gateway JWT audience.')
@minLength(1)
param authAudience string

@description('Expected Entra tenant claim for Gateway management identities.')
@minLength(36)
@maxLength(36)
param authTenantId string

@description('Server-owned app-only identity to ETS tenant/workspace scope map.')
@minLength(2)
param authAppScopeMapJson string

@description('Durable Graph subscription state JSON. Empty until #390 subscription provisioning.')
param graphSubscriptionJson string = ''

@description('Governed Microsoft health policy JSON. Empty until live #390 posture is enabled.')
param microsoftHealthPolicyJson string = ''

@description('SharePoint poll cadence in seconds.')
@minValue(30)
@maxValue(3600)
param pollIntervalSeconds int = 60

var resourceToken = uniqueString(resourceGroup().id, environmentName, connectorInstanceId)
var gatewayName = take('ets-${resourceToken}-gw', 32)
var gatewayIdentityName = take('ets-${resourceToken}-gw-id', 128)
var registryPullIdentityName = take('ets-${resourceToken}-gw-pull', 128)
var stateStorageAccountName = take('etsgw${resourceToken}', 24)
// Rotate the Q1 state share instead of deleting the prior forensic share. The live Gateway
// remains single-replica while SQLite is used; #445 replaces network-file SQLite before production.
var stateFileShareName = 'ets-gateway-state-q1-v2'
var stateKeyVaultName = take('ets-${resourceToken}-gkv', 24)
var stateStorageSecretName = 'azure-files-account-key'
var environmentStorageName = take('ets-${resourceToken}-state-q1-v2', 32)
var keyVaultSecretsUserRoleId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '4633458b-17de-408a-b874-0445c86b69e6'
)

resource managedEnvironment 'Microsoft.App/managedEnvironments@2026-01-01' existing = {
  name: managedEnvironmentName
}

resource gatewayIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: gatewayIdentityName
  location: location
}

resource registryPullIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: registryPullIdentityName
  location: location
}

module registryPull './modules/acr-pull-role.bicep' = {
  name: 'ets-gateway-acr-pull-${resourceToken}'
  scope: resourceGroup(containerRegistryResourceGroup)
  params: {
    registryName: containerRegistryName
    principalId: registryPullIdentity.properties.principalId
    pullRoleDefinitionId: containerRegistryPullRoleDefinitionId
  }
}

resource stateStorage 'Microsoft.Storage/storageAccounts@2025-06-01' = {
  name: stateStorageAccountName
  location: location
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    allowCrossTenantReplication: false
    allowSharedKeyAccess: true
    defaultToOAuthAuthentication: true
    minimumTlsVersion: 'TLS1_2'
    publicNetworkAccess: 'Enabled'
    supportsHttpsTrafficOnly: true
  }
}

resource fileService 'Microsoft.Storage/storageAccounts/fileServices@2025-06-01' = {
  parent: stateStorage
  name: 'default'
  properties: {}
}

resource stateShare 'Microsoft.Storage/storageAccounts/fileServices/shares@2025-06-01' = {
  parent: fileService
  name: stateFileShareName
  properties: {
    accessTier: 'TransactionOptimized'
    enabledProtocols: 'SMB'
    shareQuota: 5
  }
}

resource stateKeyVault 'Microsoft.KeyVault/vaults@2025-05-01' = {
  name: stateKeyVaultName
  location: location
  properties: {
    tenantId: subscription().tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
    enablePurgeProtection: true
    enabledForDeployment: false
    enabledForDiskEncryption: false
    enabledForTemplateDeployment: false
    publicNetworkAccess: 'Enabled'
  }
}

resource stateStorageSecret 'Microsoft.KeyVault/vaults/secrets@2025-05-01' = {
  parent: stateKeyVault
  name: stateStorageSecretName
  properties: {
    contentType: 'Azure Files account key for ETS Gateway managed-environment storage only'
    value: stateStorage.listKeys().keys[0].value
  }
}

resource environmentStateSecretReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(stateKeyVault.id, managedEnvironment.id, keyVaultSecretsUserRoleId)
  scope: stateKeyVault
  properties: {
    roleDefinitionId: keyVaultSecretsUserRoleId
    principalId: managedEnvironment.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

resource environmentStorage 'Microsoft.App/managedEnvironments/storages@2026-01-01' = {
  parent: managedEnvironment
  name: environmentStorageName
  properties: {
    azureFile: {
      accessMode: 'ReadWrite'
      accountKeyVaultProperties: {
        identity: 'System'
        keyVaultUrl: '${stateKeyVault.properties.vaultUri}secrets/${stateStorageSecret.name}'
      }
      accountName: stateStorage.name
      shareName: stateShare.name
    }
  }
  dependsOn: [
    environmentStateSecretReader
  ]
}

resource gateway 'Microsoft.App/containerApps@2026-01-01' = {
  name: gatewayName
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${gatewayIdentity.id}': {}
      '${registryPullIdentity.id}': {}
    }
  }
  properties: {
    environmentId: managedEnvironment.id
    configuration: {
      activeRevisionsMode: 'Single'
      identitySettings: [
        {
          identity: gatewayIdentity.id
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
      volumes: [
        {
          name: 'gateway-state'
          storageName: environmentStorage.name
          storageType: 'AzureFile'
          // Azure Files SMB uses mandatory byte-range locks that caused the Q1 Python SQLite
          // runtime to fail at startup. This is a single-replica qualification compatibility
          // setting only; #445 replaces SQLite-on-network-files before production/multi-replica use.
          mountOptions: 'nobrl'
        }
      ]
      containers: [
        {
          name: 'ets-gateway'
          image: containerImage
          command: [
            'python'
          ]
          args: [
            '-m'
            'ets.gateway.container_entrypoint'
          ]
          env: [
            {
              name: 'ETS_GATEWAY_STATE_DIR'
              value: '/var/lib/ets'
            }
            {
              name: 'ETS_GATEWAY_MANIFEST_DIR'
              value: '/app/config/connectors/enterprise'
            }
            {
              name: 'ETS_GATEWAY_MANAGED_IDENTITY_CLIENT_ID'
              value: gatewayIdentity.properties.clientId
            }
            {
              name: 'ETS_GATEWAY_CORE_BASE_URL'
              value: coreBaseUrl
            }
            {
              name: 'ETS_GATEWAY_CORE_SCOPE'
              value: coreScope
            }
            {
              name: 'ETS_GATEWAY_TENANT_ID'
              value: etsTenantId
            }
            {
              name: 'ETS_GATEWAY_WORKSPACE_ID'
              value: etsWorkspaceId
            }
            {
              name: 'ETS_GATEWAY_INSTANCE_ID'
              value: connectorInstanceId
            }
            {
              name: 'ETS_GATEWAY_SOURCE_ID'
              value: sourceId
            }
            {
              name: 'ETS_GATEWAY_SOURCE_PRINCIPAL'
              value: sourcePrincipal
            }
            {
              name: 'ETS_GATEWAY_MICROSOFT_TENANT_ID'
              value: microsoftTenantId
            }
            {
              name: 'ETS_GATEWAY_MICROSOFT_APPLICATION_ID'
              value: gatewayIdentity.properties.clientId
            }
            {
              name: 'ETS_GATEWAY_SHAREPOINT_DRIVE_ID'
              value: sharePointDriveId
            }
            {
              name: 'ETS_GATEWAY_POLL_INTERVAL_SECONDS'
              value: string(pollIntervalSeconds)
            }
            {
              name: 'ETS_GATEWAY_GRAPH_SUBSCRIPTION_JSON'
              value: graphSubscriptionJson
            }
            {
              name: 'ETS_GATEWAY_MICROSOFT_HEALTH_POLICY_JSON'
              value: microsoftHealthPolicyJson
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
            {
              name: 'ETS_AUTH_TENANT_ID'
              value: authTenantId
            }
            {
              name: 'ETS_AUTH_APP_SCOPE_MAP_JSON'
              value: authAppScopeMapJson
            }
          ]
          volumeMounts: [
            {
              volumeName: 'gateway-state'
              mountPath: '/var/lib/ets'
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
              failureThreshold: 12
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
              periodSeconds: 15
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
    environmentStorage
  ]
}

output gatewayManagedIdentityResourceId string = gatewayIdentity.id
output gatewayManagedIdentityClientId string = gatewayIdentity.properties.clientId
output registryPullIdentityResourceId string = registryPullIdentity.id
output gatewayContainerAppName string = gateway.name
output gatewayInternalIngressFqdn string = gateway.properties.configuration.ingress.fqdn
output gatewayStateStorageAccountName string = stateStorage.name
output gatewayStateFileShareName string = stateShare.name
