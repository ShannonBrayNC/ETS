targetScope = 'subscription'

@description('Short deployment name used in resource names.')
param deploymentName string = 'ets'

@description('Azure region for the resource group and regional resources.')
param location string = deployment().location

@allowed([
  'free'
  'standard'
])
@description('Deployment tier. Free uses Azure Static Web Apps Free plus a Consumption Functions plan. Standard upgrades the web plan and enables production-oriented settings.')
param tier string = 'free'

@description('Optional tags applied to all supported resources.')
param tags object = {}

@description('Deploy the API Function App. Disable for a dashboard-only proof of concept.')
param deployApi bool = true

var suffix = uniqueString(subscription().subscriptionId, deploymentName)
var normalizedName = toLower(replace(deploymentName, '_', '-'))
var resourceGroupName = 'rg-${normalizedName}-${suffix}'
var storageName = take(replace('st${normalizedName}${suffix}', '-', ''), 24)
var functionName = take('func-${normalizedName}-${suffix}', 60)
var staticWebAppName = take('swa-${normalizedName}-${suffix}', 40)
var staticWebAppSku = tier == 'free' ? 'Free' : 'Standard'

resource resourceGroup 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: resourceGroupName
  location: location
  tags: union(tags, {
    'ets:deployment': deploymentName
    'ets:tier': tier
    'ets:managed-by': 'ets-azure-configurator'
  })
}

module application 'modules/application.bicep' = {
  name: 'application-${deploymentName}'
  scope: resourceGroup
  params: {
    location: location
    deploymentName: normalizedName
    suffix: suffix
    storageName: storageName
    functionName: functionName
    staticWebAppName: staticWebAppName
    staticWebAppSku: staticWebAppSku
    deployApi: deployApi
    tier: tier
    tags: union(tags, {
      'ets:deployment': deploymentName
      'ets:tier': tier
      'ets:managed-by': 'ets-azure-configurator'
    })
  }
}

output resourceGroupName string = resourceGroup.name
output dashboardHostname string = application.outputs.dashboardHostname
output functionHostname string = application.outputs.functionHostname
output tier string = tier
output upgradeCommand string = 'pwsh ./scripts/azure/Invoke-EtsAzureConfigurator.ps1 -Mode Upgrade -Tier standard -DeploymentName ${deploymentName} -Location ${location}'
