@description('Azure region for ETS hosted support resources.')
param location string = resourceGroup().location

@description('Environment name used to compose resource names. Do not use customer data.')
param environmentName string

@description('Existing or operator-provisioned signing key name. Private key material is never in this template.')
param signingKeyName string

@description('Operator-approved signing key version stored in deployment configuration.')
param signingKeyVersion string

var suffix = toLower(replace(environmentName, '_', '-'))

resource managedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'ets-${suffix}-identity'
  location: location
}

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: 'ets-${suffix}-kv'
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
  }
}

resource appConfig 'Microsoft.AppConfiguration/configurationStores@2023-03-01' = {
  name: 'ets-${suffix}-appcfg'
  location: location
  sku: {
    name: 'standard'
  }
  properties: {
    disableLocalAuth: true
    enablePurgeProtection: true
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: 'ets-${suffix}-appi'
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    DisableLocalAuth: true
  }
}

resource signingMode 'Microsoft.AppConfiguration/configurationStores/keyValues@2023-03-01' = {
  parent: appConfig
  name: 'ETS_SIGNING_MODE'
  properties: {
    value: 'azure_key_vault'
  }
}

resource managedIdentityEnabled 'Microsoft.AppConfiguration/configurationStores/keyValues@2023-03-01' = {
  parent: appConfig
  name: 'ETS_AZURE_MANAGED_IDENTITY_ENABLED'
  properties: {
    value: 'true'
  }
}

resource vaultUrl 'Microsoft.AppConfiguration/configurationStores/keyValues@2023-03-01' = {
  parent: appConfig
  name: 'ETS_AZURE_KEY_VAULT_URL'
  properties: {
    value: keyVault.properties.vaultUri
  }
}

resource keyName 'Microsoft.AppConfiguration/configurationStores/keyValues@2023-03-01' = {
  parent: appConfig
  name: 'ETS_AZURE_KEY_NAME'
  properties: {
    value: signingKeyName
  }
}

resource keyVersion 'Microsoft.AppConfiguration/configurationStores/keyValues@2023-03-01' = {
  parent: appConfig
  name: 'ETS_AZURE_KEY_VERSION'
  properties: {
    value: signingKeyVersion
  }
}

output managedIdentityResourceId string = managedIdentity.id
output appConfigurationEndpoint string = appConfig.properties.endpoint
output keyVaultUri string = keyVault.properties.vaultUri
output applicationInsightsName string = appInsights.name
