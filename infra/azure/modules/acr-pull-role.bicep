@description('Existing Azure Container Registry name.')
@minLength(5)
param registryName string

@description('Object ID of the user-assigned managed identity that pulls images.')
@minLength(1)
param principalId string

@description('Built-in pull role. Use AcrPull for RBAC-only registries or Container Registry Repository Reader for ABAC-enabled registries.')
@allowed([
  '7f951dda-4ed3-4680-a7ca-43fe172d538d'
  'b93aa761-3e63-49ed-ac28-beffa264f7ac'
])
param pullRoleDefinitionId string

resource registry 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: registryName
}

var pullRoleResourceId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  pullRoleDefinitionId
)

resource registryPullRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(registry.id, principalId, pullRoleResourceId)
  scope: registry
  properties: {
    roleDefinitionId: pullRoleResourceId
    principalId: principalId
    principalType: 'ServicePrincipal'
  }
}

output loginServer string = registry.properties.loginServer
output registryResourceId string = registry.id
