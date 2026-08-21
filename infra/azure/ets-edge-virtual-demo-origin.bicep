@description('Azure region for the isolated Edge Virtual demo origin.')
param location string = resourceGroup().location

@description('Deterministic non-customer environment seed used only for Azure resource names.')
@minLength(1)
param environmentName string = 'edge-virtual-demo'

@description('Existing private Azure Container Registry name.')
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

@description('Immutable Edge API OCI image. Deployment automation MUST require repository@sha256:<digest>.')
@minLength(1)
param edgeApiImage string

@description('Immutable Edge protected-ingress/BFF OCI image. Deployment automation MUST require repository@sha256:<digest>.')
@minLength(1)
param edgeWebhookImage string

@description('Immutable Edge synthetic upstream OCI image. Deployment automation MUST require repository@sha256:<digest>.')
@minLength(1)
param edgeUpstreamImage string

@description('Immutable hosted Dark Pro UI OCI image. Deployment automation MUST require repository@sha256:<digest>.')
@minLength(1)
param edgeUiImage string

@description('Exact browser origin allowed to submit state-changing hosted BFF requests.')
@minLength(8)
param publicDemoOrigin string = 'https://edge-demo.lanternprotocol.net'

@description('Synthetic ETS tenant identifier. Never use customer identifiers in this demo profile.')
@minLength(1)
param syntheticTenantId string = 'tenant_edge_demo'

@description('Synthetic ETS workspace identifier. Never use customer identifiers in this demo profile.')
@minLength(1)
param syntheticWorkspaceId string = 'workspace_edge_demo'

@description('VNet address space reserved for the isolated hosted Edge Virtual environment.')
param vnetAddressPrefix string = '10.84.0.0/24'

@description('Dedicated Container Apps infrastructure subnet. Workload-profile environments require /27 or larger and Microsoft.App/environments delegation.')
param infrastructureSubnetPrefix string = '10.84.0.0/27'

var resourceToken = uniqueString(resourceGroup().id, environmentName)
var vnetName = take('ets-${resourceToken}-edge-vnet', 64)
var infrastructureSubnetName = 'container-apps'
var managedEnvironmentName = take('ets-${resourceToken}-edge-cae', 60)
var containerAppName = take('ets-${resourceToken}-edge-demo', 32)
var registryPullIdentityName = take('ets-${resourceToken}-edge-pull', 128)
var infrastructureSubnetId = resourceId(
  'Microsoft.Network/virtualNetworks/subnets',
  vnetName,
  infrastructureSubnetName
)

resource registryPullIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: registryPullIdentityName
  location: location
}

module registryPull './modules/acr-pull-role.bicep' = {
  name: 'ets-edge-demo-acr-pull-${resourceToken}'
  scope: resourceGroup(containerRegistryResourceGroup)
  params: {
    registryName: containerRegistryName
    principalId: registryPullIdentity.properties.principalId
    pullRoleDefinitionId: containerRegistryPullRoleDefinitionId
  }
}

resource vnet 'Microsoft.Network/virtualNetworks@2024-05-01' = {
  name: vnetName
  location: location
  properties: {
    addressSpace: {
      addressPrefixes: [
        vnetAddressPrefix
      ]
    }
    subnets: [
      {
        name: infrastructureSubnetName
        properties: {
          addressPrefix: infrastructureSubnetPrefix
          delegations: [
            {
              name: 'container-apps-environment'
              properties: {
                serviceName: 'Microsoft.App/environments'
              }
            }
          ]
          privateEndpointNetworkPolicies: 'Enabled'
          privateLinkServiceNetworkPolicies: 'Enabled'
        }
      }
    ]
  }
}

resource managedEnvironment 'Microsoft.App/managedEnvironments@2026-01-01' = {
  name: managedEnvironmentName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'azure-monitor'
    }
    publicNetworkAccess: 'Disabled'
    vnetConfiguration: {
      infrastructureSubnetId: infrastructureSubnetId
      internal: true
    }
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
    zoneRedundant: false
  }
  dependsOn: [
    vnet
  ]
}

resource containerApp 'Microsoft.App/containerApps@2025-01-01' = {
  name: containerAppName
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${registryPullIdentity.id}': {}
    }
  }
  properties: {
    environmentId: managedEnvironment.id
    configuration: {
      activeRevisionsMode: 'Single'
      identitySettings: [
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
        external: true
        allowInsecure: false
        targetPort: 8080
        transport: 'auto'
      }
    }
    template: {
      containers: [
        {
          name: 'edge-api'
          image: edgeApiImage
          env: [
            {
              name: 'ETS_EDGE_DATA_DIR'
              value: '/var/lib/ets'
            }
            {
              name: 'ETS_STORAGE_PROVIDER'
              value: 'sqlite'
            }
            {
              name: 'ETS_SQLITE_PATH'
              value: '/var/lib/ets/edge.db'
            }
            {
              name: 'ETS_LOG_ID'
              value: 'ets-edge-virtual-azure-demo'
            }
            {
              name: 'ETS_REDACTION_PROFILE'
              value: 'none'
            }
            {
              name: 'ETS_AUTH_MODE'
              value: 'local_api_key'
            }
            {
              name: 'ETS_SIGNING_MODE'
              value: 'ed25519'
            }
            {
              name: 'ETS_SIGNING_PUBLIC_KEY_ID'
              value: 'ets-edge-virtual-azure-demo-key'
            }
          ]
          resources: {
            cpu: json('0.75')
            memory: '1.5Gi'
          }
          volumeMounts: [
            {
              volumeName: 'edge-data'
              mountPath: '/var/lib/ets'
            }
          ]
        }
        {
          name: 'edge-bff'
          image: edgeWebhookImage
          env: [
            {
              name: 'ETS_EDGE_API_URL'
              value: 'http://127.0.0.1:8001/internal/edge-api'
            }
            {
              name: 'ETS_EDGE_API_ORIGIN'
              value: 'http://127.0.0.1:8000'
            }
            {
              name: 'ETS_EDGE_API_KEY_FILE'
              value: '/var/lib/ets/edge-local-api-key'
            }
            {
              name: 'ETS_EDGE_DEVICE_IDENTITY_FILE'
              value: '/var/lib/ets/edge-device-identity.json'
            }
            {
              name: 'ETS_EDGE_SYNC_DB'
              value: '/var/lib/ets/edge-sync.db'
            }
            {
              name: 'ETS_EDGE_SYNC_MAX_ITEMS'
              value: '500'
            }
            {
              name: 'ETS_EDGE_SYNC_MAX_BYTES'
              value: '16777216'
            }
            {
              name: 'ETS_EDGE_UPSTREAM_URL'
              value: 'http://127.0.0.1:8002'
            }
            {
              name: 'ETS_EDGE_SYSLOG_ENABLED'
              value: '0'
            }
            {
              name: 'ETS_EDGE_UI_BFF_ENABLED'
              value: '1'
            }
            {
              name: 'ETS_EDGE_UI_ALLOWED_ORIGIN'
              value: publicDemoOrigin
            }
            {
              name: 'ETS_EDGE_UI_TENANT'
              value: syntheticTenantId
            }
            {
              name: 'ETS_EDGE_UI_WORKSPACE'
              value: syntheticWorkspaceId
            }
            {
              name: 'ETS_EDGE_UI_SOURCE_ID'
              value: 'edge-dark-pro-azure-demo'
            }
            {
              name: 'ETS_EDGE_FLEET_ENROLLMENT_STATE'
              value: 'not_configured'
            }
            {
              name: 'ETS_EDGE_FLEET_HEARTBEAT_STATE'
              value: 'not_configured'
            }
          ]
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          volumeMounts: [
            {
              volumeName: 'edge-data'
              mountPath: '/var/lib/ets'
            }
          ]
        }
        {
          name: 'edge-upstream'
          image: edgeUpstreamImage
          env: [
            {
              name: 'ETS_EDGE_UPSTREAM_DB'
              value: '/var/lib/ets-upstream/upstream.db'
            }
          ]
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
          volumeMounts: [
            {
              volumeName: 'edge-upstream'
              mountPath: '/var/lib/ets-upstream'
            }
          ]
        }
        {
          name: 'edge-ui'
          image: edgeUiImage
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/afd-healthz'
                port: 8080
                scheme: 'HTTP'
              }
              initialDelaySeconds: 5
              periodSeconds: 15
              timeoutSeconds: 2
              failureThreshold: 3
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/afd-healthz'
                port: 8080
                scheme: 'HTTP'
              }
              initialDelaySeconds: 3
              periodSeconds: 10
              timeoutSeconds: 2
              failureThreshold: 3
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 1
      }
      volumes: [
        {
          name: 'edge-data'
          storageType: 'EmptyDir'
        }
        {
          name: 'edge-upstream'
          storageType: 'EmptyDir'
        }
      ]
    }
  }
}

output managedEnvironmentId string = managedEnvironment.id
output managedEnvironmentName string = managedEnvironment.name
output containerAppId string = containerApp.id
output containerAppName string = containerApp.name
output privateOriginFqdn string = containerApp.properties.configuration.ingress.fqdn
output publicNetworkAccess string = managedEnvironment.properties.publicNetworkAccess
output virtualIpMode string = 'internal'
output runtimeIdentityCount int = 0
output registryPullIdentityClientId string = registryPullIdentity.properties.clientId
