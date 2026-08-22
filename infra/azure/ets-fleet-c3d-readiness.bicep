@description('Azure region for the existing Fleet managed environment.')
param location string = resourceGroup().location

@description('Existing internal Fleet Container Apps managed environment name.')
@minLength(1)
param managedEnvironmentName string

@description('Existing Fleet Container App private FQDN.')
@minLength(1)
param fleetPrivateOriginFqdn string

@description('Existing Fleet runtime user-assigned identity resource ID.')
@minLength(1)
param runtimeIdentityResourceId string

@description('Existing approved private Azure Container Registry login server.')
@minLength(1)
param registryServer string

@description('Approved immutable Fleet image.')
@minLength(1)
param fleetImage string

@description('Bounded private readiness job name.')
@minLength(2)
@maxLength(32)
param readinessJobName string

resource managedEnvironment 'Microsoft.App/managedEnvironments@2026-01-01' existing = {
  name: managedEnvironmentName
}

resource readinessJob 'Microsoft.App/jobs@2025-01-01' = {
  name: readinessJobName
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${runtimeIdentityResourceId}': {}
    }
  }
  properties: {
    environmentId: managedEnvironment.id
    configuration: {
      triggerType: 'Manual'
      manualTriggerConfig: {
        parallelism: 1
        replicaCompletionCount: 1
      }
      replicaRetryLimit: 0
      replicaTimeout: 300
      identitySettings: [
        {
          identity: runtimeIdentityResourceId
          lifecycle: 'None'
        }
      ]
      registries: [
        {
          server: registryServer
          identity: runtimeIdentityResourceId
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'fleet-readiness'
          image: fleetImage
          command: [
            'python'
            '-m'
            'ets.fleet.private_readiness_probe'
          ]
          env: [
            {
              name: 'ETS_FLEET_INTERNAL_BASE_URL'
              value: 'https://${fleetPrivateOriginFqdn}'
            }
          ]
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
          probes: []
          volumeMounts: []
        }
      ]
      initContainers: []
      volumes: []
    }
  }
}

output readinessJobName string = readinessJob.name
