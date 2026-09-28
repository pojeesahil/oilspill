import json
import sys
from pathlib import Path

from oilspill.api.backend.vessels.temporal_risk import calculate_temporal_risk
from oilspill.api.backend.environment.dynamic_queue import build_dynamic_queue


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def add_contextual_events(temporal_scenario, contextual_data):
    vessels = {vessel["mmsi"]: vessel for vessel in temporal_scenario["vessels"]}
    configured_types = temporal_scenario["risk_config"]["event_weights"]

    for contextual_vessel in contextual_data["vessels"]:
        mmsi = contextual_vessel["mmsi"]
        if mmsi not in vessels:
            raise ValueError(f"No temporal-risk scenario entry for {mmsi}")

        for event in contextual_vessel["events"]:
            if event["type"] not in configured_types:
                raise ValueError(
                    f"Add a weight for '{event['type']}' under "
                    "risk_config.event_weights in the temporal scenario"
                )
            vessels[mmsi]["events"].append(event)

    return temporal_scenario


def main():
    if len(sys.argv) != 4:
        raise SystemExit(
            "Usage: python -m backend.environment.contextual_queue "
            "BASE_QUEUE.json TEMPORAL_SCENARIO.json CONTEXTUAL_SIGNALS.json"
        )

    queue_data = read_json(sys.argv[1])
    temporal_scenario = read_json(sys.argv[2])
    contextual_data = read_json(sys.argv[3])

    add_contextual_events(temporal_scenario, contextual_data)
    temporal_result = calculate_temporal_risk(temporal_scenario)
    result = build_dynamic_queue(queue_data, temporal_result)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()