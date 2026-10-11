"""Budget gate uses captured billing, regional retail prices, and dated exchange rates."""

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "reports/evidence"


def load(name):
    return json.loads((EVIDENCE / name).read_text())


def calculate(days=7, active_hours=3, training_usd=0):
    billing = load("azure-course-spending.json")["properties"]
    if billing.get("nextLink"):
        raise ValueError("Incomplete billing pages cannot establish remaining allowance")
    exchange = load("exchange-rate.json")
    fx = exchange["usd_thb"]
    columns = [c["name"] for c in billing["columns"]]
    spent = 0
    for row in billing["rows"]:
        item = dict(zip(columns, row))
        currency = item["Currency"]
        if currency not in {"USD", "THB"}:
            raise ValueError("Unrecognized billing currency")
        spent += item["Cost"] * (fx if currency == "USD" else 1)
    remaining = max(0, 800 - spent)
    prices = load("azure-retail-prices.json")["items"]

    def rate(service, meter, product=None, sku=None, tier=None):
        found = [
            p
            for p in prices
            if p["serviceName"] == service
            and p["meterName"] == meter
            and (not product or p["productName"] == product)
            and (not sku or p["skuName"] == sku)
            and (tier is None or p["tierMinimumUnits"] == tier)
            and p["retailPrice"] > 0
        ]
        if not found:
            raise ValueError(f"No verified regional price for {service}/{meter}")
        return max(p["retailPrice"] for p in found)

    rates = {
        "cpu_second": rate("Azure Container Apps", "Standard vCPU Active Usage"),
        "gib_second": rate("Azure Container Apps", "Standard Memory Active Usage"),
        "million_requests": rate("Azure Container Apps", "Standard Requests"),
        "registry_day": rate("Container Registry", "Basic Registry Unit"),
        "storage_gb_month": rate("Storage", "Hot LRS Data Stored", "General Block Blob v2", "Hot LRS"),
        "log_ingestion_gb": rate("Log Analytics", "Analytics Logs Data Ingestion"),
        "log_alert_month": rate("Azure Monitor", "Alerts System Log Monitored at 5 Minute Frequency"),
    }
    costs = {
        "serving": active_hours * 3600 * 2 * (2 * rates["cpu_second"] + 4 * rates["gib_second"]) + 0.01,
        "storage": 2 * days / 30 * rates["storage_gb_month"] + 0.05,
        "registry": days * rates["registry_day"],
        "monitoring": days * 0.1 * rates["log_ingestion_gb"] + days / 30 * rates["log_alert_month"],
        "training": training_usd,
    }
    forecast = sum(costs.values()) * fx * 1.25
    result = {
        "allowance_thb": 800,
        "conservative_prior_subscription_spend_thb": spent,
        "remaining_allowance_thb": remaining,
        "exchange": exchange,
        "rates_usd": rates,
        "forecast_usd_by_component": costs,
        "forecast_thb_including_25_percent_margin": forecast,
        "assumptions": {
            "retention_days": days,
            "active_hours_max_two_replicas": active_hours,
            "log_cap_gb_day": 0.1,
            "blob_gb": 2,
            "log_alert_frequency_minutes": 5,
            "training": "local MPS; no cloud training charges",
            "free_grants": "excluded conservatively",
            "egress": "Serving resources share East Asia. One-time DVC downloads and other transfer are unitemized; verify lagged billing before retaining resources.",
        },
        "billing_budget_usd_rounded_down": math.floor(remaining / fx),
        "passed": forecast <= remaining,
    }
    (EVIDENCE / "budget-forecast.json").write_text(json.dumps(result, indent=2) + "\n")
    if not result["passed"]:
        raise RuntimeError(
            f"Deployment blocked: {forecast:.2f} THB forecast exceeds {remaining:.2f} THB remaining"
        )
    return result


if __name__ == "__main__":
    print(json.dumps(calculate(), indent=2))
