# How data scientists would detect an accuracy drop

**Status: proposed operating procedure; not implemented.** This document explains the missing production model-quality feedback loop. It does not claim that accuracy monitoring, a labeling pipeline, or accuracy alerts currently exist.

The direct answer is: **collect a representative sample of production predictions, obtain independent correct labels, compare predictions with those labels on a schedule, and notify the data scientist when quality crosses an agreed threshold.** Without correct labels, the team can detect suspicious changes, but cannot establish that accuracy has dropped.

## What this capstone can detect today

| Existing evidence | What it tells the team | What it cannot establish |
|---|---|---|
| HTTP errors, latency, `/health`, and `/ready` in [service/app.py](../service/app.py) | Whether the API and model are available and responding correctly at the service level | Whether a successful prediction has the correct roast label |
| `coffee_predictions_total{predicted_class=...}` | How often each roast class is predicted | Whether those predictions match reality |
| Optical guard and [local camera alert](../monitoring/alert_rules.yml) | Covered-camera or uniform-glare inputs are being rejected | Accuracy on images that pass the guard |
| Azure camera-rejection rule and email Action Group, described in [README](../README.md) | An existing route for notifying the configured recipient about camera issues | An accuracy alert or delivery to a data-science team |
| [Selected model metadata](model_metadata.json) | Offline test accuracy and macro-F1 of 1.0000 on 181 deduplicated held-out images | Current production accuracy on new cameras, lighting, or bean origins |

The 100% offline score is a historical result on a small test set. It is not a promise of 100% live accuracy. The [model card](model_card.md) also states that confidence is uncalibrated: a confidence of 0.99 does not prove that a prediction is correct.

## Proposed feedback loop

1. **Capture sampled predictions.** A future client collector or service extension would persist the response together with the `X-Request-ID` response header, prediction timestamp, model version, image identifier/hash, predicted class, all four probabilities, and camera/site information. Preserve the sampled image in access-controlled storage long enough for review. Use a unique internal prediction-record ID as well, since the API accepts client-supplied request IDs. Today's request logs contain request ID, model version, status, and latency; they do not persist prediction probabilities or images for this evaluation.
2. **Obtain independent ground truth.** A trained roast reviewer labels sampled images as `Dark`, `Green`, `Light`, or `Medium` using an agreed labeling rubric, preferably supported by known batch roast records. Hide the prediction during labeling to reduce anchoring. Resolve disagreements with a second reviewer. Record reviewer, label timestamp, and label status; retain ambiguous or out-of-scope cases separately. Never use the model's own prediction as its correct label.
3. **Build a representative labeled cohort.** Randomly sample accepted production images across days, cameras, and operating conditions. Deduplicate repeated frames and test/demo traffic. Keep additional complaint or low-confidence samples for investigation, but report them separately so they do not bias the overall accuracy estimate. Track rejected inputs separately from classification accuracy.
4. **Evaluate on a schedule.** Initially review results weekly; automate a daily batch evaluation when volume supports it. Join finalized labels to the original predictions using the unique record ID. Evaluate each model version separately, using prediction time to define the cohort and displaying label completeness and delay. Late labels should update that cohort's report rather than be treated as correct predictions or new traffic.
5. **Notify the responsible people.** A future evaluation job would publish a quality report and evaluate the rules below. A future Azure quality alert could route through an Action Group to the designated data scientist and service owner. This needs its own quality results, alert configuration, recipients, and delivery test; the camera alert cannot calculate accuracy by itself. Until automation exists, a named reviewer can perform the same weekly review and manually notify those owners.

If nobody can supply trustworthy labels, report production accuracy as **unknown** and arrange periodic expert audits. Do not substitute confidence, HTTP success rate, or predicted-class counts for accuracy.

## Metrics, baseline, and proposed intervention rules

For labeled, accepted predictions:

```text
accuracy = number of predictions matching the reviewed label / number of finalized labeled predictions
drop in percentage points = 100 × (baseline accuracy − current accuracy)
```

Report accuracy, macro-F1, per-class recall and support, a confusion matrix, sample size, label coverage, and a 95% confidence interval for accuracy. Use macro-F1 and per-class recall to expose errors that an overall score might hide when class proportions change. See the [scikit-learn model evaluation documentation](https://scikit-learn.org/stable/modules/model_evaluation.html#classification-metrics).

Establish and freeze a reference from an initial expert-reviewed production sample under accepted operating conditions, separately for each model version. Do not silently move the reference downward when quality worsens. Until this reference exists, use the provisional absolute floor below and show the offline result only as context. Compare camera/site slices as well as the aggregate so a shift in traffic mix does not conceal a local problem.

These are **illustrative starting rules for this capstone**, not measured or deployed requirements. The data scientist and project owner should tune them to review capacity, baseline uncertainty, and the cost of roast errors.

| Signal | Proposed trigger | Required response |
|---|---|---|
| Accuracy degradation | Accuracy below 95%, or at least 5 percentage points below the frozen production reference | Notify the data scientist and service owner for investigation |
| Class-specific degradation | Recall below 90% for any roast class with at least 30 reviewed examples | Inspect that class and its confusion pairs even if overall accuracy passes |
| Insufficient evidence | Fewer than 200 finalized labels in the latest non-overlapping weekly cohort, or fewer than 30 for a class | Mark the relevant result as insufficient data; request more labels and review known failures |
| Missing feedback | No new finalized labels for seven days while production predictions continue | Notify the labeling owner; show accuracy as stale |
| Early warning | Sustained change in confidence, class proportions, or image characteristics relative to the reference | Investigate inputs and prioritize additional labeling; do not declare an accuracy drop from this alone |

For the overall accuracy rule, require at least 200 finalized labels per weekly cohort. A first eligible breach opens an investigation; persistence in a second non-overlapping cohort escalates it. These counts are practical review targets, not a guarantee of statistical significance: review confidence intervals and baseline uncertainty before declaring a confirmed decline. Serious verified failures can justify intervention immediately without waiting for the next cohort.

For low traffic, use a longer, explicitly dated cohort and disclose the slower detection time. A healthy monitor must distinguish “no decline detected” from “too little labeled data.” Confidence-based early warnings would require additional persisted response data; class proportions are already exposed as counters. Input-distribution changes are drift signals, as described in [Google's monitoring overview](https://docs.cloud.google.com/gemini-enterprise-agent-platform/machine-learning/model-monitoring/overview), and still require label-based evaluation to assess correctness.

## What the data scientist receives and does

An alert should include the model version, cohort dates, current and baseline metrics, labeled sample count and coverage, confidence interval, affected classes/cameras, and a link to the report and reviewed errors. Detection delay includes sampling, human labeling, and evaluation time; this is not an instantaneous accuracy alarm.

For example, suppose an accepted production reference is 98%, and 184 of 200 new reviewed predictions are correct. Current accuracy is 92%, a six-percentage-point drop. That breaches both proposed accuracy rules and opens an investigation. This is a hypothetical example, not a capstone measurement.

The response procedure would be:

1. **Validate the evidence.** Confirm labels, joins, model version, duplicate removal, and cohort representativeness. Examine errors and the confusion matrix; separate labeling mistakes from model mistakes.
2. **Check the cause.** The service owner checks artifact/version changes and preprocessing. The camera operator checks lighting, lens cleanliness, and camera configuration. The data scientist checks new bean origins, class mix, and systematic class confusion.
3. **Choose a targeted correction.** Repair capture conditions or preprocessing when those caused the problem. If representative new images expose a model limitation, curate and version reviewed data, retrain through the existing MLflow/DVC workflow, and compare the candidate with the current model. A recent release regression may justify restoring a previously verified revision if it performs better on the affected images.
4. **Validate before promotion.** Use validation data for development and an independently held-out evaluation set for the final comparison. Keep monitoring samples used for training out of that evaluation. Do not repeatedly tune against the capstone's original 181-image test set. Retain the existing artifact, parity, API, and performance checks; they complement quality evaluation.
5. **Verify recovery.** After a controlled release or operational fix, collect fresh reviewed production samples. Close the incident after two eligible non-overlapping cohorts meet the quality rules, and record cause, action, and recovery evidence. Reset a production reference only through an explicit reviewed decision.

For the presentation: “Our current alerts detect camera and service problems. To know whether roast accuracy drops, we would compare sampled live predictions with expert labels, calculate accuracy and class-level metrics on a schedule, and alert the data scientist when agreed quality thresholds are breached. That feedback loop is documented future work.”
