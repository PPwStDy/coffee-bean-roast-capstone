targetScope = 'resourceGroup'
param location string = 'eastasia'
param imageDigest string
param environmentId string
param identityId string
param registry string
param modelVersion string
param appName string = 'coffee6688218-api'
param revisionSuffix string
param previousRevision string = ''
var tags = { course: 'itcs355', student: '6688218', lab: 'capstone' }

resource app 'Microsoft.App/containerApps@2024-03-01' = {
  name: appName
  location: location
  tags: tags
  identity: { type: 'UserAssigned', userAssignedIdentities: { '${identityId}': {} } }
  properties: {
    managedEnvironmentId: environmentId
    workloadProfileName: 'Consumption'
    configuration: {
      activeRevisionsMode: 'Multiple'
      ingress: {
        external: true
        targetPort: 8080
        transport: 'auto'
        allowInsecure: false
        traffic: empty(previousRevision) ? [{ latestRevision: true, weight: 100 }] : [{ revisionName: previousRevision, weight: 100 }]
      }
      registries: [{ server: registry, identity: identityId }]
    }
    template: {
      revisionSuffix: revisionSuffix
      containers: [{
        name: 'api'
        image: imageDigest
        resources: { cpu: 2, memory: '4Gi' }
        env: [
          { name: 'MODEL_VERSION', value: modelVersion }
          { name: 'INFERENCE_THREADS', value: '1' }
          { name: 'MAX_INFERENCE_CONCURRENCY', value: '2' }
        ]
        probes: [
          { type: 'Liveness', httpGet: { path: '/health', port: 8080 }, periodSeconds: 30, timeoutSeconds: 5 }
          { type: 'Readiness', httpGet: { path: '/ready', port: 8080 }, periodSeconds: 10, timeoutSeconds: 5 }
          { type: 'Startup', httpGet: { path: '/ready', port: 8080 }, periodSeconds: 5, failureThreshold: 60, timeoutSeconds: 5 }
        ]
      }]
      scale: { minReplicas: 0, maxReplicas: 2, rules: [{ name: 'http', http: { metadata: { concurrentRequests: '2' } } }] }
    }
  }
}
output url string = 'https://${app.properties.configuration.ingress.fqdn}'
output revision string = app.properties.latestRevisionName
