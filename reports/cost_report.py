"""Report deployed serving costs separately from persistent components and training."""

import json
from pathlib import Path

from cloudlayer.budget import calculate


def main():
    budget = calculate()
    evidence = Path("reports/evidence")
    warm_path = evidence / "deployed-warm.json"
    report = {
        "pricing_source": "https://prices.azure.com/api/retail/prices",
        "budget": budget,
        "serving_cost_per_1000": None,
        "status": "waiting_for_deployed_benchmark",
        "training_cloud_usd": 0,
        "training_compute": "local MPS; local electricity not measured",
        "persistent_component_forecast_usd": budget["forecast_usd_by_component"],
    }
    if warm_path.exists():
        warm = json.loads(warm_path.read_text())
        r = budget["rates_usd"]
        # Full configured maximum for the entire measured duration is a conservative allocation bound.
        cpu_seconds = 2 * 2 * warm["duration_seconds"]
        gib_seconds = 2 * 4 * warm["duration_seconds"]
        total = (
            cpu_seconds * r["cpu_second"]
            + gib_seconds * r["gib_second"]
            + warm["requests"] / 1_000_000 * r["million_requests"]
        )
        per1000 = total * 1000 / warm["requests"]
        report.update(
            status="measured_duration_with_configured_allocation_upper_bound",
            serving_cost_per_1000={
                "usd": per1000,
                "thb": per1000 * budget["exchange"]["usd_thb"],
                "measured_requests": warm["requests"],
                "duration_seconds": warm["duration_seconds"],
                "vCPU_per_replica": 2,
                "GiB_per_replica": 4,
                "maximum_replicas": 2,
                "assumption": "Both replicas active for the full benchmark; excludes free grants. Not an invoice or exact measured replica-seconds.",
            },
        )
    (evidence / "cost-summary.json").write_text(json.dumps(report, indent=2) + "\n")
    text = "# Cost report\n\n"
    text += "Official East Asia retail rates and dated ECB currency conversion are captured under reports/evidence.\n\n"
    text += f"Conservative remaining allowance: {budget['remaining_allowance_thb']:.2f} THB. Seven-day forecast with 25% margin: {budget['forecast_thb_including_25_percent_margin']:.2f} THB.\n\n"
    if report["serving_cost_per_1000"]:
        serving = report["serving_cost_per_1000"]
        text += f"Serving per 1,000 predictions: at most ${serving['usd']:.6f} / {serving['thb']:.4f} THB under the documented maximum-allocation assumption, using {serving['duration_seconds']:.2f} measured seconds.\n\n"
    else:
        text += "Serving cost per1,000 is pending deployed measurements. The old 50ms/512MiB estimate is withdrawn.\n\n"
    text += "| Component | Seven-day USD forecast |\n|---|---:|\n"
    for component, value in budget["forecast_usd_by_component"].items():
        text += f"| {component} | {value:.6f} |\n"
    text += "\nRegistry and monitoring continue to charge while serving is scaled to zero. Budget notifications are alerts, not a spending shutdown. The deployment gate blocks an over-budget forecast, and scoped teardown removes persistent resources. Billing can lag, so the forecast includes margin. One-time DVC downloads and other network transfer are not itemized in this estimate. Local device and electricity costs are unmeasured. Temporary alert diagnosis rules are documented separately from the retained production rule.\n"
    Path("reports/cost_report.md").write_text(text)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
