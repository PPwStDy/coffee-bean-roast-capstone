# Cost report

Official East Asia retail rates and dated ECB currency conversion are captured under reports/evidence.

Conservative remaining allowance: 635.98 THB. Seven-day forecast with 25% margin: 239.09 THB.

Serving cost per1,000 is pending deployed measurements. The old 50ms/512MiB estimate is withdrawn.

| Component | Seven-day USD forecast |
|---|---:|
| serving | 1.306000 |
| storage | 0.061200 |
| registry | 1.166200 |
| monitoring | 3.171000 |
| training | 0.000000 |

Registry and monitoring continue to charge while serving is scaled to zero. Budget notifications are alerts, not a spending shutdown. The deployment gate blocks an over-budget forecast, and scoped teardown removes persistent resources. Billing can lag, so the forecast includes margin.
