param location string
param deploymentName string
param suffix string
param storageName string
param functionName string
param staticWebAppName string
param staticWebAppSku string
param deployApi bool
param tier string
param tags object

resource staticWebApp 'Microsoft.Web/staticSites@2023-12-01' = {
  name: staticWebAppName
  location: location
  tags: tags
  sku: {
    name: staticWebAppSku
    tier: staticWebAppSku
  }
  properties: {
    allowConfigFileUpdates: true
  }
}

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = if (deployApi) {
  name: storageName
  location: location
  tags: tags
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    allowBlobPublicAccess: false
    allowSharedKeyAccess: true
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
  }
}

resource consumptionPlan 'Microsoft.Web/serverfarms@2023-12-01' = if (deployApi) {
  name: 'plan-${deploymentName}-${suffix}'
  location: location
  tags: tags
  sku: {
    name: 'Y1'
    tier: 'Dynamic'
  }
  properties: {
    reserved: true
  }
}

resource functionApp 'Microsoft.Web/sites@2023-12-01' = if (deployApi) {
  name: functionName
  location: location
  tags: tags
  kind: 'functionapp,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: consumptionPlan.id
    httpsOnly: true
    clientAffinityEnabled: false
    siteConfig: {
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
      http20Enabled: true
      linuxFxVersion: 'Python|3.12'
      alwaysOn: false
      appSettings: [
        {
          name: 'FUNCTIONS_EXTENSION_VERSION'
          value: '~4'
        }
        {
          name: 'FUNCTIONS_WORKER_RUNTIME'
          value: 'python'
        }
        {
          name: 'AzureWebJobsStorage'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storage.name};EndpointSuffix=${environment().suffixes.storage};AccountKey=${storage.listKeys().keys[0].value}'
        }
        {
          name: 'ETS_DEPLOYMENT_TIER'
          value: tier
        }
        {
          name: 'ETS_DASHBOARD_HOSTNAME'
          value: staticWebApp.properties.defaultHostname
        }
      ]
    }
  }
}

output dashboardHostname string = staticWebApp.properties.defaultHostname
output functionHostname string = deployApi ? functionApp.properties.defaultHostName : ''
