@description('Azure region for the live private Fleet C3D substrate.')
param location string = resourceGroup().location

@description('Deterministic non-customer seed for the live Fleet substrate.')
@minLength(1)
param environmentName string = 'fleet-live-c3d'

@description('Existing approved private Azure Container Registry name.')
@minLength(5)
param containerRegistryName string

@description('Resource group containing the approved private ACR.')
@minLength(1)
param containerRegistryResourceGroup string

@description('Registry pull role for the approved ACR posture.')
@allowed([
  '7f951dda-4ed3-4680-a7ca-43fe172d538d'
  'b93aa761-3e63-49ed-ac28-beffa264f7ac'
])
param containerRegistryPullRoleDefinitionId string = '7f951dda-4ed3-4680-a7ca-43fe172d538d'

@description('Approved immutable Fleet image in repository@sha256:digest form.')
@minLength(1)
param fleetImage string

@description('Microsoft Entra tenant identifier accepted by Fleet.')
@minLength(1)
param fleetEntraTenantId string

@description('Exact Microsoft Entra issuer accepted by Fleet.')
@minLength(8)
param fleetEntraIssuer string

@description('Exact Microsoft Entra audience accepted by Fleet.')
@minLength(1)
param fleetEntraAudience string

@description('Fleet PostgreSQL database name.')
@minLength(1)
param fleetPostgresDatabase string = 'fleet'

@description('PostgreSQL high-availability mode.')
@allowed([
  'Disabled'
  'SameZone'
  'ZoneRedundant'
])
param postgresHighAvailabilityMode string = 'ZoneRedundant'

var token = uniqueString(resourceGroup().id, environmentName)
var runtimeIdentityName = take('ets-${token}-fleet-runtime', 128)
var runtimeIdentityResourceId = resourceId(
  'Microsoft.ManagedIdentity/userAssignedIdentities',
  runtimeIdentityName
)
var migrationIdentityName = take('ets-${token}-fleet-migration', 128)
var migrationJobName = take('ets-${token}-fleet-migrate', 32)

resource migrationIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: migrationIdentityName
  location: location
}

module migrationRegistryPull './modules/acr-pull-role.bicep' = {
  name: 'ets-fleet-c3d-migration-acr-pull-${token}'
  scope: resourceGroup(containerRegistryResourceGroup)
  params: {
    registryName: containerRegistryName
    principalId: migrationIdentity.properties.principalId
    pullRoleDefinitionId: containerRegistryPullRoleDefinitionId
  }
}

module fleetC3b './ets-fleet-c3b.bicep' = {
  name: 'ets-fleet-c3d-substrate-${token}'
  params: {
    location: location
    environmentName: environmentName
    containerRegistryName: containerRegistryName
    containerRegistryResourceGroup: containerRegistryResourceGroup
    containerRegistryPullRoleDefinitionId: containerRegistryPullRoleDefinitionId
    fleetImage: fleetImage
    fleetEntraTenantId: fleetEntraTenantId
    fleetEntraIssuer: fleetEntraIssuer
    fleetEntraAudience: fleetEntraAudience
    postgresEntraAdministratorObjectId: migrationIdentity.properties.principalId
    postgresEntraAdministratorName: migrationIdentity.name
    postgresEntraAdministratorType: 'ServicePrincipal'
    fleetPostgresUser: runtimeIdentityName
    fleetPostgresDatabase: fleetPostgresDatabase
    postgresHighAvailabilityMode: postgresHighAvailabilityMode
  }
}

resource migrationJob 'Microsoft.App/jobs@2025-01-01' = {
  name: migrationJobName
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${migrationIdentity.id}': {}
      '${runtimeIdentityResourceId}': {}
    }
  }
  properties: {
    environmentId: fleetC3b.outputs.managedEnvironmentId
    configuration: {
      triggerType: 'Manual'
      manualTriggerConfig: {
        parallelism: 1
        replicaCompletionCount: 1
      }
      replicaRetryLimit: 0
      replicaTimeout: 900
      identitySettings: [
        {
          identity: migrationIdentity.id
          lifecycle: 'None'
        }
        {
          identity: runtimeIdentityResourceId
          lifecycle: 'None'
        }
      ]
      registries: [
        {
          server: migrationRegistryPull.outputs.loginServer
          identity: migrationIdentity.id
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'fleet-migration'
          image: fleetImage
          command: [
            'python'
            '-m'
            'ets.fleet.bootstrap'
          ]
          env: [
            {
              name: 'AZURE_CLIENT_ID'
              value: migrationIdentity.properties.clientId
            }
            {
              name: 'ETS_FLEET_POSTGRES_HOST'
              value: fleetC3b.outputs.postgresPrivateFqdn
            }
            {
              name: 'ETS_FLEET_POSTGRES_DATABASE'
              value: fleetPostgresDatabase
            }
            {
              name: 'ETS_FLEET_POSTGRES_MIGRATION_USER'
              value: migrationIdentity.name
            }
            {
              name: 'ETS_FLEET_RUNTIME_POSTGRES_ROLE'
              value: runtimeIdentityName
            }
            {
              name: 'ETS_FLEET_RUNTIME_PRINCIPAL_ID'
              value: fleetC3b.outputs.fleetRuntimeIdentityPrincipalId
            }
            {
              name: 'ETS_FLEET_RUNTIME_CLIENT_ID'
              value: fleetC3b.outputs.fleetRuntimeIdentityClientId
            }
          ]
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          probes: []
          volumeMounts: []
        }
      ]
      initContainers: []
      volumes: []
    }
  }
  dependsOn: [
    migrationRegistryPull
    fleetC3b
  ]
}

output fleetContainerAppName string = fleetC3b.outputs.fleetContainerAppName
output fleetPrivateOriginFqdn string = fleetC3b.outputs.fleetPrivateOriginFqdn
output managedEnvironmentName string = fleetC3b.outputs.managedEnvironmentName
output managedEnvironmentId string = fleetC3b.outputs.managedEnvironmentId
output fleetRuntimeIdentityName string = runtimeIdentityName
output fleetRuntimeIdentityClientId string = fleetC3b.outputs.fleetRuntimeIdentityClientId
output fleetRuntimeIdentityPrincipalId string = fleetC3b.outputs.fleetRuntimeIdentityPrincipalId
output migrationIdentityName string = migrationIdentity.name
output migrationIdentityClientId string = migrationIdentity.properties.clientId
output migrationIdentityPrincipalId string = migrationIdentity.properties.principalId
output migrationJobName string = migrationJob.name
output postgresServerName string = fleetC3b.outputs.postgresServerName
output postgresPrivateFqdn string = fleetC3b.outputs.postgresPrivateFqdn
output fleetDatabaseName string = fleetPostgresDatabase
output immutableFleetImage string = fleetImage
output publicHostnameActivated bool = false
