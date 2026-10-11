# Evidence records

Successful checks and failed attempts are retained separately. A generated script or template is implementation evidence, not proof that a live operation succeeded.

- `contract-tests.txt`: 29 API hardening and dataset tests passed against the historical serving artifact.
- `model-tests.txt`: 3 model behavior checks passed against the historical artifact.
- `optical-regression-drill.json`: guard removal in isolated source caused the expected failures.
- `container-endpoint-checks.json`: real Linux baseline container passed startup, four-class predictions, version consistency, optical rejection and malformed input checks.
- Azure quota, policy, permission, pricing and spending records support the deployment preflight. Initial foundation provisioning failures are retained; only a Succeeded deployment is completion evidence.
- `training-attempt-mps32.json`: memory pressure stopped the first run before an epoch completed. The completed 20-epoch run used batch 8 MPS with Docker stopped and took 1,346 seconds.

Final release, remote CI, deployed benchmarks, delivered alert, costs and teardown require their own successful records. Local baseline checks do not establish clean model generalization or deployed performance.

## Clean release results

- `clean-restoration.json` and `clean-release-restoration.json`: fresh checkout data and release restored from the shared Azure DVC remote.
- `azure-ml-release.json`: clean release registered in the shared workspace as version 1.
- `final-tests.xml`: 43 passing local checks, including seven regional Azure management tests.
- `local-alert-delivery.log`: Alertmanager delivered the actual firing occlusion alert to the local webhook.
- `local-grafana.png`: local operational dashboard capture.
- `image-digest.json`: private registry upload digest; actual deployed digest is recorded separately in candidate deployment evidence.
- `ci-success.json`: completed passing GitHub CI with Linux container integration.

Training lineage and float/INT8 validation comparison are retained in the immutable DVC release. Its single selected-release test evaluation scored 181/181; source/camera generalization remains unmeasured.
