# Evidence records

Successful checks and failed attempts are retained separately. A generated script or template is implementation evidence, not proof that a live operation succeeded.

- `contract-tests.txt`: 29 API hardening and dataset tests passed against the historical serving artifact.
- `model-tests.txt`: 3 model behavior checks passed against the historical artifact.
- `optical-regression-drill.json`: guard removal in isolated source caused the expected failures.
- `container-endpoint-checks.json`: real Linux baseline container passed startup, four-class predictions, version consistency, optical rejection and malformed input checks.
- Azure quota, policy, permission, pricing and spending records support the deployment preflight. Initial foundation provisioning failures are retained; only a Succeeded deployment is completion evidence.
- `training-attempt-mps32.json`: memory pressure stopped the first run before an epoch completed. The next run uses batch8 on MPS with Docker stopped.

Final release, remote CI, deployed benchmarks, delivered alert, costs and teardown require their own successful records. Local baseline checks do not establish clean model generalization or deployed performance.
