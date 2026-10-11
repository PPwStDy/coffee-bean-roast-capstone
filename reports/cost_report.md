# Cost report

Official East Asia retail rates and dated ECB currency conversion are captured under reports/evidence.

Conservative remaining allowance: 635.52 THB. Seven-day forecast with 25% margin: 239.09 THB.

Serving per 1,000 predictions: at most $0.010970 / 0.3678 THB under the documented maximum-allocation assumption, using 88.09 measured seconds.

| Component | Seven-day USD forecast |
|---|---:|
| serving | 1.306000 |
| storage | 0.061200 |
| registry | 1.166200 |
| monitoring | 3.171000 |
| training | 0.000000 |

Registry and monitoring continue to charge while serving is scaled to zero. Budget notifications are alerts, not a spending shutdown. The deployment gate blocks an over-budget forecast, and scoped teardown removes persistent resources. Billing can lag, so the forecast includes margin.
