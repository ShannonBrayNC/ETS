@description('Azure region used by the existing qualification Container Apps environment.')
param location string

@description('Ephemeral qualification Container Apps Job name.')
@minLength(2)
@maxLength(32)
param clientName string

@description('Existing Container Apps managed environment name deployed by HOST-AZ-C.')
@minLength(1)
param managedEnvironmentName string

@description('Dedicated user-assigned identity used only for private registry image pull.')
@minLength(1)
param registryPullIdentityResourceId string

@description('Private Azure Container Registry login server.')
@minLength(1)
param registryServer string

@description('Immutable Q1 image reference by digest.')
@minLength(1)
param containerImage string

@description('Internal ETS API base URL visible only within the Container Apps environment.')
@minLength(1)
param baseUrl string

@description('GitHub Actions run identifier used only for synthetic qualification metadata.')
@minLength(1)
param runId string

@description('Synthetic qualification tenant identifier.')
@minLength(1)
param tenantId string

@description('Synthetic qualification workspace identifier.')
@minLength(1)
param workspaceId string

@secure()
@description('Protected synthetic production-JWKS bearer token. Never output or retain this value.')
param bearerToken string

resource managedEnvironment 'Microsoft.App/managedEnvironments@2026-01-01' existing = {
  name: managedEnvironmentName
}

resource qualificationClient 'Microsoft.App/jobs@2025-01-01' = {
  name: clientName
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${registryPullIdentityResourceId}': {}
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
      replicaTimeout: 600
      identitySettings: [
        {
          identity: registryPullIdentityResourceId
          lifecycle: 'None'
        }
      ]
      registries: [
        {
          server: registryServer
          identity: registryPullIdentityResourceId
        }
      ]
      secrets: [
        {
          name: 'q1-token'
          value: bearerToken
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'q1-client'
          image: containerImage
          command: [
            'python'
            '/app/scripts/qualify_hosted_azure_live.py'
          ]
          args: [
            'pre'
            '--base-url'
            baseUrl
            '--run-id'
            runId
            '--tenant-id'
            tenantId
            '--workspace-id'
            workspaceId
          ]
          env: [
            {
              name: 'ETS_Q1_BEARER_TOKEN'
              secretRef: 'q1-token'
            }
          ]
          probes: []
          volumeMounts: []
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
        }
      ]
      initContainers: []
      volumes: []
    }
  }
}

output qualificationClientName string = qualificationClient.name
output registryPullIdentityResourceId string = registryPullIdentityResourceId
