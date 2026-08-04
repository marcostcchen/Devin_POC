// The whole platform, as one resource group: a small AKS cluster and a registry
// to pull project images from. Everything above this line is Helm.
//
//   az deployment group create -g <rg> -f main.bicep -p @parameters.json
//
// This is the prototype's cluster, not a production one: a single node pool, no
// private networking and no hardening beyond the AKS defaults.

@description('Prefix for every resource name; must be unique enough within the subscription.')
param name string = 'pocplatform'

param location string = resourceGroup().location

@description('Size of the single node pool. Two small nodes are enough for a handful of POCs.')
param nodeSize string = 'Standard_D2s_v5'

@minValue(1)
@maxValue(5)
param nodeCount int = 2

@description('Kubernetes version; leave empty to take the cluster default.')
param kubernetesVersion string = ''

var clusterName = '${name}-aks'
var registryName = toLower(replace('${name}acr', '-', ''))

resource registry 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  name: registryName
  location: location
  sku: { name: 'Basic' }
  properties: {
    adminUserEnabled: false
  }
}

resource cluster 'Microsoft.ContainerService/managedClusters@2024-05-01' = {
  name: clusterName
  location: location
  identity: { type: 'SystemAssigned' }
  properties: {
    dnsPrefix: clusterName
    kubernetesVersion: empty(kubernetesVersion) ? null : kubernetesVersion
    enableRBAC: true
    agentPoolProfiles: [
      {
        name: 'system'
        mode: 'System'
        osType: 'Linux'
        vmSize: nodeSize
        count: nodeCount
        enableAutoScaling: false
        // Room for the ingress controller and the projects.
        maxPods: 60
      }
    ]
    networkProfile: {
      networkPlugin: 'azure'
      networkPluginMode: 'overlay'
      loadBalancerSku: 'standard'
      outboundType: 'loadBalancer'
    }
  }
}

// Let the cluster pull project images without any credential in a manifest.
resource acrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: registry
  name: guid(registry.id, cluster.id, 'AcrPull')
  properties: {
    principalId: cluster.properties.identityProfile.kubeletidentity.objectId
    principalType: 'ServicePrincipal'
    // AcrPull
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      '7f951dda-4ed3-4680-a7ca-43fe172d538d'
    )
  }
}

output clusterName string = cluster.name
output registryLoginServer string = registry.properties.loginServer
