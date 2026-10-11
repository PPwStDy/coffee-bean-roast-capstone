targetScope = 'subscription'
param capstoneGroup string = 'rg-itcs355-6688218-capstone'
param remainingAllowanceTHB int
@description('Remaining allowance converted to billing currency and rounded down, never up')
param billingBudgetAmount int
param alertEmail string
param startDate string
param endDate string
resource budget 'Microsoft.Consumption/budgets@2023-11-01' = {
  name: 'itcs355-6688218-capstone'
  properties: {
    category: 'Cost'
    amount: billingBudgetAmount
    timeGrain: 'Monthly'
    timePeriod: { startDate: startDate, endDate: endDate }
    filter: { dimensions: { name: 'ResourceGroupName', operator: 'In', values: [capstoneGroup] } }
    notifications: {
      Half: { enabled: true, operator: 'GreaterThanOrEqualTo', threshold: 50, thresholdType: 'Actual', contactEmails: [alertEmail] }
      Warning: { enabled: true, operator: 'GreaterThanOrEqualTo', threshold: 80, thresholdType: 'Actual', contactEmails: [alertEmail] }
      Limit: { enabled: true, operator: 'GreaterThanOrEqualTo', threshold: 100, thresholdType: 'Actual', contactEmails: [alertEmail] }
    }
  }
}
output allowanceTHB int = remainingAllowanceTHB
