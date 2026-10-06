@description('Short prefix for resource names')
param prefix string = 'vnetapi'

param location string = resourceGroup().location

@description('Client ID of the Entra ID app registration used to sign users in')
param authClientId string

var storageName = toLower('${prefix}${uniqueString(resourceGroup().id)}')
// Built-in role: Network Contributor
var networkContributorRoleId = '4d97b98b-1d4f-4787-a291-c67834d212e7'

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageName
  location: location
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
  }
}

resource plan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: '${prefix}-plan'
  location: location
  kind: 'linux'
  sku: { name: 'Y1', tier: 'Dynamic' }
  properties: { reserved: true }
}

resource functionApp 'Microsoft.Web/sites@2023-12-01' = {
  name: '${prefix}-${uniqueString(resourceGroup().id)}'
  location: location
  kind: 'functionapp,linux'
  identity: { type: 'SystemAssigned' }
  properties: {
    serverFarmId: plan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'Python|3.12'
      appSettings: [
        { name: 'FUNCTIONS_EXTENSION_VERSION', value: '~4' }
        { name: 'FUNCTIONS_WORKER_RUNTIME', value: 'python' }
        { name: 'AzureWebJobsStorage', value: 'DefaultEndpointsProtocol=https;AccountName=${storage.name};AccountKey=${storage.listKeys().keys[0].value};EndpointSuffix=${environment().suffixes.storage}' }
        { name: 'STORAGE_CONNECTION_STRING', value: 'DefaultEndpointsProtocol=https;AccountName=${storage.name};AccountKey=${storage.listKeys().keys[0].value};EndpointSuffix=${environment().suffixes.storage}' }
        { name: 'AZURE_SUBSCRIPTION_ID', value: subscription().subscriptionId }
      ]
    }
  }
}

// Lets the function's managed identity create VNETs in this resource group
resource networkRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, functionApp.id, networkContributorRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', networkContributorRoleId)
    principalId: functionApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// Easy Auth: every request must carry a valid Entra ID token, otherwise 401.
// No role or group checks, so any authenticated user is authorized.
resource auth 'Microsoft.Web/sites/config@2023-12-01' = {
  parent: functionApp
  name: 'authsettingsV2'
  properties: {
    platform: { enabled: true }
    globalValidation: {
      requireAuthentication: true
      unauthenticatedClientAction: 'Return401'
    }
    identityProviders: {
      azureActiveDirectory: {
        enabled: true
        registration: {
          openIdIssuer: '${environment().authentication.loginEndpoint}${tenant().tenantId}/v2.0'
          clientId: authClientId
        }
        validation: {
          allowedAudiences: [ 'api://${authClientId}' ]
        }
      }
    }
  }
}

output functionAppName string = functionApp.name
output functionAppHostname string = functionApp.properties.defaultHostName
