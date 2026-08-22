@description('Azure region for the private Fleet C3B control plane.')
param location string = resourceGroup().location

@description('Non-customer deployment seed used only for deterministic resource names.')
@minLength(1)
param environmentName string = 'fleet-c3b'

@description('Existing private Azure Container Registry name.')
@minLength(5)
param containerRegistryName string

@description('Resource group containing the existing Azure Container Registry.')
@minLength(1)
param containerRegistryResourceGroup string

@description('Registry pull role: AcrPull for RBAC-only ACR, or Repository Reader for ABAC-enabled ACR.')
@allowed([
  '7f951dda-4ed3-4680-a7ca-43fe172d538d'
  'b93aa761-3e63-49ed-ac28-beffa264f7ac'
])
param containerRegistryPullRoleDefinitionId string = '7f951dda-4ed3-4680-a7ca-43fe172d538d'

@description('Immutable Fleet OCI image. Deployment automation MUST require repository@sha256:<digest>.')
@minLength(1)
param fleetImage string

@description('Microsoft Entra tenant identifier accepted by the Fleet BFF.')
@minLength(1)
param fleetEntraTenantId string

@description('Exact HTTPS issuer accepted by the Fleet BFF.')
@minLength(8)
param fleetEntraIssuer string

@description('Exact application audience accepted by the Fleet BFF.')
@minLength(1)
param fleetEntraAudience string

@description('Object ID of the PostgreSQL Microsoft Entra administrator.')
@minLength(1)
param postgresEntraAdministratorObjectId string

@description('Display name of the PostgreSQL Microsoft Entra administrator.')
@minLength(1)
param postgresEntraAdministratorName string

@description('Principal type of the PostgreSQL Microsoft Entra administrator.')
@allowed([
  'Group'
  'ServicePrincipal'
  'User'
])
param postgresEntraAdministratorType string = 'Group'

@description('PostgreSQL role mapped to the Fleet runtime managed identity during controlled bootstrap.')
@minLength(1)
param fleetPostgresUser string

@description('Fleet PostgreSQL database name.')
@minLength(1)
param fleetPostgresDatabase string = 'fleet'

@description('General Purpose PostgreSQL SKU.')
param postgresSkuName string = 'Standard_D2ds_v5'

@description('PostgreSQL high-availability mode. ZoneRedundant is preferred where the region supports it.')
@allowed([
  'Disabled'
  'SameZone'
  'ZoneRedundant'
])
param postgresHighAvailabilityMode string = 'ZoneRedundant'

@description('VNet address space reserved for the private Fleet production environment.')
param vnetAddressPrefix string = '10.86.0.0/23'

@description('Dedicated Container Apps infrastructure subnet.')
param infrastructureSubnetPrefix string = '10.86.0.0/27'

@description('Dedicated private-endpoint subnet.')
param privateEndpointSubnetPrefix string = '10.86.0.32/27'

var token = uniqueString(resourceGroup().id, environmentName)
var vnetName = take('ets-${token}-fleet-vnet', 64)
var infrastructureSubnetName = 'container-apps'
var privateEndpointSubnetName = 'private-endpoints'
var environmentNameResolved = take('ets-${token}-fleet-cae', 60)
var appName = take('ets-${token}-fleet', 32)
var runtimeIdentityName = take('ets-${token}-fleet-runtime', 128)
var postgresName = take('ets-${token}-fleet-pg', 63)
var postgresPrivateEndpointName = take('ets-${token}-fleet-pg-pe', 80)
var postgresPrivateDnsZoneName = 'privatelink.postgres.database.azure.com'
var infrastructureSubnetId = resourceId(
  'Microsoft.Network/virtualNetworks/subnets',
  vnetName,
  infrastructureSubnetName
)
var privateEndpointSubnetId = resourceId(
  'Microsoft.Network/virtualNetworks/subnets',
  vnetName,
  privateEndpointSubnetName
)

resource runtimeIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: runtimeIdentityName
  location: location
}

module registryPull './modules/acr-pull-role.bicep' = {
  name: 'ets-fleet-c3b-acr-pull-${token}'
  scope: resourceGroup(containerRegistryResourceGroup)
  params: {
    registryName: containerRegistryName
    principalId: runtimeIdentity.properties.principalId
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
        }
      }
      {
        name: privateEndpointSubnetName
        properties: {
          addressPrefix: privateEndpointSubnetPrefix
          privateEndpointNetworkPolicies: 'Disabled'
        }
      }
    ]
  }
}

resource managedEnvironment 'Microsoft.App/managedEnvironments@2026-01-01' = {
  name: environmentNameResolved
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

resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2025-08-01' = {
  name: postgresName
  location: location
  sku: {
    name: postgresSkuName
    tier: 'GeneralPurpose'
  }
  properties: {
    authConfig: {
      activeDirectoryAuth: 'Enabled'
      passwordAuth: 'Disabled'
      tenantId: fleetEntraTenantId
    }
    backup: {
      backupRetentionDays: 14
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: {
      mode: postgresHighAvailabilityMode
    }
    network: {
      publicNetworkAccess: 'Disabled'
    }
    storage: {
      storageSizeGB: 64
    }
  }
}

resource postgresAdministrator 'Microsoft.DBforPostgreSQL/flexibleServers/administrators@2025-08-01' = {
  parent: postgres
  name: postgresEntraAdministratorObjectId
  properties: {
    principalName: postgresEntraAdministratorName
    principalType: postgresEntraAdministratorType
    tenantId: fleetEntraTenantId
  }
}

resource fleetDatabase 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2025-08-01' = {
  parent: postgres
  name: fleetPostgresDatabase
  properties: {
    charset: 'UTF8'
    collation: 'en_US.UTF8'
  }
  dependsOn: [
    postgresAdministrator
  ]
}

resource postgresPrivateDnsZone 'Microsoft.Network/privateDnsZones@2024-06-01' = {
  name: postgresPrivateDnsZoneName
  location: 'global'
}

resource postgresPrivateDnsVnetLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = {
  parent: postgresPrivateDnsZone
  name: 'fleet-vnet'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: {
      id: vnet.id
    }
  }
}

resource postgresPrivateEndpoint 'Microsoft.Network/privateEndpoints@2024-05-01' = {
  name: postgresPrivateEndpointName
  location: location
  properties: {
    subnet: {
      id: privateEndpointSubnetId
    }
    privateLinkServiceConnections: [
      {
        name: 'postgresql'
        properties: {
          privateLinkServiceId: postgres.id
          groupIds: [
            'postgresqlServer'
          ]
          privateLinkServiceConnectionState: {
            status: 'Approved'
            description: 'ETS Fleet C3B private PostgreSQL origin'
            actionsRequired: 'None'
          }
        }
      }
    ]
  }
  dependsOn: [
    vnet
  ]
}

resource postgresPrivateDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-05-01' = {
  parent: postgresPrivateEndpoint
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'postgres'
        properties: {
          privateDnsZoneId: postgresPrivateDnsZone.id
        }
      }
    ]
  }
  dependsOn: [
    postgresPrivateDnsVnetLink
  ]
}

resource fleetApp 'Microsoft.App/containerApps@2025-01-01' = {
  name: appName
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${runtimeIdentity.id}': {}
    }
  }
  properties: {
    environmentId: managedEnvironment.id
    configuration: {
      activeRevisionsMode: 'Single'
      identitySettings: [
        {
          identity: runtimeIdentity.id
          lifecycle: 'None'
        }
      ]
      registries: [
        {
          server: registryPull.outputs.loginServer
          identity: runtimeIdentity.id
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
          name: 'fleet-bff'
          image: fleetImage
          env: [
            {
              name: 'AZURE_CLIENT_ID'
              value: runtimeIdentity.properties.clientId
            }
            {
              name: 'ETS_FLEET_POSTGRES_HOST'
              value: postgres.properties.fullyQualifiedDomainName
            }
            {
              name: 'ETS_FLEET_POSTGRES_DATABASE'
              value: fleetDatabase.name
            }
            {
              name: 'ETS_FLEET_POSTGRES_USER'
              value: fleetPostgresUser
            }
            {
              name: 'ETS_FLEET_ENTRA_ISSUER'
              value: fleetEntraIssuer
            }
            {
              name: 'ETS_FLEET_ENTRA_AUDIENCE'
              value: fleetEntraAudience
            }
            {
              name: 'ETS_FLEET_ENTRA_TENANT_ID'
              value: fleetEntraTenantId
            }
          ]
          resources: {
            cpu: json('0.75')
            memory: '1.5Gi'
          }
          probes: [
            {
              type: 'Liveness'
              tcpSocket: {
                port: 8080
              }
              initialDelaySeconds: 10
              periodSeconds: 20
              timeoutSeconds: 3
              failureThreshold: 3
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/fleet/readyz'
                port: 8080
                scheme: 'HTTP'
              }
              initialDelaySeconds: 5
              periodSeconds: 10
              timeoutSeconds: 3
              failureThreshold: 3
            }
          ]
        }
      ]
      scale: {
        minReplicas: 2
        maxReplicas: 6
        rules: [
          {
            name: 'http-concurrency'
            http: {
              metadata: {
                concurrentRequests: '50'
              }
            }
          }
        ]
      }
    }
  }
  dependsOn: [
    fleetDatabase
    postgresPrivateDnsZoneGroup
  ]
}

output managedEnvironmentId string = managedEnvironment.id
output managedEnvironmentName string = managedEnvironment.name
output fleetContainerAppId string = fleetApp.id
output fleetContainerAppName string = fleetApp.name
output fleetPrivateOriginFqdn string = fleetApp.properties.configuration.ingress.fqdn
output fleetRuntimeIdentityClientId string = runtimeIdentity.properties.clientId
output fleetRuntimeIdentityPrincipalId string = runtimeIdentity.properties.principalId
output postgresServerId string = postgres.id
output postgresServerName string = postgres.name
output postgresServerVersion string = postgres.properties.version
output postgresPrivateFqdn string = postgres.properties.fullyQualifiedDomainName
output publicHostnameActivated bool = false
output corePublicEndpointCreated bool = false
output gatewayPublicEndpointCreated bool = false
output iotPublicManagementEndpointCreated bool = false
