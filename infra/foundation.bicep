targetScope = 'resourceGroup'
param location string = 'eastasia'
param prefix string = 'coffee6688218'
param alertEmail string
param operatorObjectId string
// Immutable owner/repository IDs are required for repositories created after 2026-07-15.
param githubRepository string = 'PPwStDy@129304443/coffee-bean-roast-capstone@1414323298'
var tags = { course: 'itcs355', student: '6688218', lab: 'capstone' }

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: 'cf6688218${uniqueString(resourceGroup().id)}'
  location: location
  tags: tags
  kind: 'StorageV2'
  sku: { name: 'Standard_LRS' }
  properties: { minimumTlsVersion: 'TLS1_2', allowBlobPublicAccess: false, allowSharedKeyAccess: false }
}
resource blobs 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storage
  name: 'default'
  properties: { deleteRetentionPolicy: { enabled: true, days: 7 } }
}
resource container 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobs
  name: 'capstone'
  properties: { publicAccess: 'None' }
}
resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: '${prefix}${uniqueString(resourceGroup().id)}'
  location: location
  tags: tags
  sku: { name: 'Basic' }
  properties: { adminUserEnabled: false, publicNetworkAccess: 'Enabled' }
}
resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${prefix}-identity'
  location: location
  tags: tags
}
resource ciIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${prefix}-ci'
  location: location
  tags: tags
}
resource readIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${prefix}-ci-read'
  location: location
  tags: tags
}
resource githubMain 'Microsoft.ManagedIdentity/userAssignedIdentities/federatedIdentityCredentials@2023-01-31' = {
  parent: ciIdentity
  name: 'github-main'
  properties: {
    issuer: 'https://token.actions.githubusercontent.com'
    subject: 'repo:${githubRepository}:ref:refs/heads/main'
    audiences: ['api://AzureADTokenExchange']
  }
}
resource githubPR 'Microsoft.ManagedIdentity/userAssignedIdentities/federatedIdentityCredentials@2023-01-31' = {
  parent: readIdentity
  name: 'github-pull-request'
  properties: {
    issuer: 'https://token.actions.githubusercontent.com'
    subject: 'repo:${githubRepository}:pull_request'
    audiences: ['api://AzureADTokenExchange']
  }
}
var blobRole = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
resource operatorStorage 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage.id, operatorObjectId, blobRole)
  scope: storage
  properties: { principalId: operatorObjectId, principalType: 'User', roleDefinitionId: blobRole }
}
resource ciStorage 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage.id, ciIdentity.id, blobRole)
  scope: storage
  properties: { principalId: ciIdentity.properties.principalId, principalType: 'ServicePrincipal', roleDefinitionId: blobRole }
}
resource acrAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, ciIdentity.id, 'AcrPush')
  scope: acr
  properties: {
    principalId: ciIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '8311e382-0749-4cb8-b61a-304f252e45ec')
  }
}
resource contributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, ciIdentity.id, 'Contributor')
  properties: {
    principalId: ciIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'b24988ac-6180-42a0-ab88-20f7382dd24c')
  }
}
resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${prefix}-logs'
  location: location
  tags: tags
  properties: { sku: { name: 'PerGB2018' }, retentionInDays: 30, workspaceCapping: { dailyQuotaGb: json('0.1') } }
}
resource environment 'Microsoft.App/managedEnvironments@2026-07-01' = {
  name: '${prefix}-environment'
  location: location
  tags: tags
  properties: {
    environmentMode: 'WorkloadProfiles'
    workloadProfiles: [{ name: 'Consumption', workloadProfileType: 'Consumption' }]
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: { customerId: logs.properties.customerId, sharedKey: logs.listKeys().primarySharedKey }
    }
  }
}
resource action 'Microsoft.Insights/actionGroups@2023-01-01' = {
  name: '${prefix}-email'
  location: 'global'
  tags: tags
  properties: {
    groupShortName: 'roast-alert'
    enabled: true
    emailReceivers: [{ name: 'student', emailAddress: alertEmail, useCommonAlertSchema: true }]
  }
}
resource alert 'Microsoft.Insights/scheduledQueryRules@2023-12-01' = {
  name: '${prefix}-camera-occlusion'
  location: location
  tags: tags
  properties: {
    displayName: 'Camera sensor occlusion warning'
    severity: 2
    enabled: true
    scopes: [logs.id]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT5M'
    autoMitigate: true
    skipQueryValidation: true
    criteria: { allOf: [{
      query: 'union isfuzzy=true (datatable(TimeGenerated:datetime, Log_s:string)[]), ContainerAppConsoleLogs_CL | extend event=parse_json(Log_s) | where tostring(event.event) == "occlusion_guard_rejection"'
      timeAggregation: 'Count'
      operator: 'GreaterThan'
      threshold: 0
      failingPeriods: { numberOfEvaluationPeriods: 1, minFailingPeriodsToAlert: 1 }
    }] }
    actions: { actionGroups: [action.id] }
  }
}
resource workbook 'Microsoft.Insights/workbooks@2022-04-01' = {
  name: guid(resourceGroup().id, 'roast-workbook')
  location: location
  tags: tags
  kind: 'shared'
  properties: {
    displayName: 'Coffee roast API operations'
    category: 'workbook'
    sourceId: logs.id
    serializedData: replace(loadTextContent('workbook.json'), '__WORKSPACE_ID__', logs.id)
  }
}
output storageAccount string = storage.name
output blobUri string = '${storage.properties.primaryEndpoints.blob}capstone'
output registry string = acr.properties.loginServer
output environmentId string = environment.id
output identityId string = identity.id
output clientId string = ciIdentity.properties.clientId
output readClientId string = readIdentity.properties.clientId
output principalId string = ciIdentity.properties.principalId
output logAnalyticsId string = logs.id
output logAnalyticsCustomerId string = logs.properties.customerId
output actionGroupId string = action.id
output workbookId string = workbook.id

resource runtimePull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, identity.id, 'AcrPull')
  scope: acr
  properties: {
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
  }
}
resource readStorage 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage.id, readIdentity.id, 'BlobReader')
  scope: storage
  properties: {
    principalId: readIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1')
  }
}
