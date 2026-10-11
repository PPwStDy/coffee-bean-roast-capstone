targetScope = 'subscription'
param location string = 'eastasia'
param groupName string = 'rg-itcs355-6688218-capstone'
param alertEmail string
param operatorObjectId string
resource group 'Microsoft.Resources/resourceGroups@2022-09-01' = {
  name: groupName
  location: location
  tags: {
    course: 'itcs355'
    student: '6688218'
    lab: 'capstone'
  }
}
module foundation 'foundation.bicep' = {
  name: 'capstone-foundation'
  scope: group
  params: {
    location: location
    alertEmail: alertEmail
    operatorObjectId: operatorObjectId
  }
}
output configuration object = {
  storageAccount: foundation.outputs.storageAccount
  blobUri: foundation.outputs.blobUri
  registry: foundation.outputs.registry
  environmentId: foundation.outputs.environmentId
  identityId: foundation.outputs.identityId
  clientId: foundation.outputs.clientId
  readClientId: foundation.outputs.readClientId
  principalId: foundation.outputs.principalId
  logAnalyticsId: foundation.outputs.logAnalyticsId
  logAnalyticsCustomerId: foundation.outputs.logAnalyticsCustomerId
  actionGroupId: foundation.outputs.actionGroupId
  workbookId: foundation.outputs.workbookId
}
