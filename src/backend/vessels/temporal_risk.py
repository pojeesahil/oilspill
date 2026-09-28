import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path


def parse_time(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"Timestamp must include a timezone: {value}")
    return parsed.astimezone(timezone.utc)


def calculate_temporal_risk(scenario):
    config = scenario["risk_config"]
    as_of = parse_time(scenario["as_of_time"])
    half_life = float(config["half_life_hours"])
    event_weights = config["event_weights"]

    if half_life <= 0:
        raise ValueError("half_life_hours must be positive")

    results = []

    for vessel in scenario["vessels"]:
        event_details = []
        remaining = 1.0

        for event in vessel["events"]:
            event_time = parse_time(event["time"])
            severity = float(event["severity"])
            event_type = event["type"]

            if not 0 <= severity <= 1:
                raise ValueError("Event severity must be between 0 and 1")
            if event_type not in event_weights:
                raise ValueError(f"No configured weight for event type: {event_type}")

            weight = float(event_weights[event_type])
            if not 0 <= weight <= 1:
                raise ValueError(f"Weight for {event_type} must be between 0 and 1")

            age_hours = max(0.0, (as_of - event_time).total_seconds() / 3600)
            decay = math.exp(-math.log(2) * age_hours / half_life)
            contribution = weight * severity * decay

            # Combine signals with a bounded noisy-OR score.
            remaining *= 1.0 - contribution

            event_details.append({
                "time": event_time.isoformat(),
                "type": event_type,
                "severity": severity,
                "configured_weight": weight,
                "age_hours": round(age_hours, 2),
                "decay_factor": round(decay, 4),
                "current_contribution": round(contribution, 4),
            })

        results.append({
            "mmsi": vessel["mmsi"],
            "as_of_time": as_of.isoformat(),
            "temporal_risk_index": round(1.0 - remaining, 4),
            "events": event_details,
        })

    results.sort(key=lambda item: item["temporal_risk_index"], reverse=True)

    return {
        "vessels": results,
        "score_meaning": (
            "Configurable surveillance index with time-decayed signals; "
            "not a spill probability, guilt score, or validated risk estimate."
        ),
    }


def main():
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: python -m backend.vessels.temporal_risk SCENARIO.json"
        )

    scenario_path = Path(sys.argv[1])
    scenario = json.loads(scenario_path.read_text(encoding="utf-8-sig"))
    print(json.dumps(calculate_temporal_risk(scenario), indent=2))


if __name__ == "__main__":
    main()