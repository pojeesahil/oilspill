import json
import sys
from pathlib import Path


def bounded(value, label):
    value = float(value)
    if not 0 <= value <= 1:
        raise ValueError(f"{label} must be between 0 and 1")
    return value


def build_dynamic_queue(queue_data, temporal_data):
    risk_by_mmsi = {
        vessel["mmsi"]: bounded(
            vessel["temporal_risk_index"], "temporal_risk_index"
        )
        for vessel in temporal_data["vessels"]
    }

    updated = []

    for item in queue_data["queue"]:
        mmsi = item["mmsi"]
        if mmsi not in risk_by_mmsi:
            raise ValueError(f"No temporal risk result for {mmsi}")

        temporal_risk = risk_by_mmsi[mmsi]
        opportunity = bounded(item["spill_opportunity"], "spill_opportunity")
        impact = bounded(
            item["potential_impact_index"], "potential_impact_index"
        )
        uncertainty = bounded(item["data_uncertainty"], "data_uncertainty")

        incident_proxy = temporal_risk * opportunity
        priority = incident_proxy * impact * uncertainty

        updated.append({
            **item,
            "temporal_risk_index": temporal_risk,
            "incident_proxy": round(incident_proxy, 4),
            "priority_index": round(priority, 4),
        })

    updated.sort(key=lambda item: item["priority_index"], reverse=True)

    for rank, item in enumerate(updated, start=1):
        item["priority_rank"] = rank

    return {
        "scenario_label": queue_data.get("scenario_label"),
        "queue": updated,
        "score_meaning": (
            "Priority combines the time-decayed surveillance index, "
            "spill opportunity, potential impact, and data uncertainty. "
            "It is not a spill probability or guilt score."
        ),
    }


def main():
    if len(sys.argv) != 3:
        raise SystemExit(
            "Usage: python -m backend.environment.dynamic_queue "
            "BASE_QUEUE.json TEMPORAL_RISK.json"
        )

    queue_data = json.loads(
        Path(sys.argv[1]).read_text(encoding="utf-8-sig")
    )
    temporal_data = json.loads(
        Path(sys.argv[2]).read_text(encoding="utf-8-sig")
    )

    print(json.dumps(build_dynamic_queue(queue_data, temporal_data), indent=2))


if __name__ == "__main__":
    main()