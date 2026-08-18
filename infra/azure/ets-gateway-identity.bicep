@description('Azure region for the hosted Gateway identity.')
param location string = resourceGroup().location

@description('Naming seed shared with the hosted Gateway deployment.')
@minLength(1)
param environmentName string

@description('Stable Microsoft connector instance identifier shared with the Gateway deployment.')
@minLength(1)
param connectorInstanceId string

var resourceToken = uniqueString(resourceGroup().id, environmentName, connectorInstanceId)
var gatewayIdentityName = take('ets-${resourceToken}-gw-id', 128)

resource gatewayIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: gatewayIdentityName
  location: location
}

output gatewayManagedIdentityName string = gatewayIdentity.name
output gatewayManagedIdentityResourceId string = gatewayIdentity.id
output gatewayManagedIdentityClientId string = gatewayIdentity.properties.clientId
output gatewayManagedIdentityPrincipalId string = gatewayIdentity.properties.principalId
