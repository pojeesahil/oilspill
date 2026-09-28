import json
import sys
from pathlib import Path


def _condition_matches(zone, condition):
    field = condition["field"]
    operator = condition["operator"]
    expected = condition["value"]
    actual = zone.get(field)

    if actual is None:
        return False
    if operator == "gte":
        return actual >= expected
    if operator == "gt":
        return actual > expected
    if operator == "lte":
        return actual <= expected
    if operator == "lt":
        return actual < expected
    if operator == "eq":
        return actual == expected

    raise ValueError(f"Unsupported rule operator: {operator}")


def build_response_queue(impact_forecast, policy):
    rules = sorted(policy["rules"], key=lambda rule: rule["priority_rank"])
    queue = []

    for zone in impact_forecast["zones"]:
        triggered = [
            rule for rule in rules
            if all(
                _condition_matches(zone, condition)
                for condition in rule["conditions"]
            )
        ]

        actions = []
        for rule in triggered:
            actions.extend(rule["actions"])

        queue.append({
            "zone": zone["name"],
            "exposure_fraction": zone["exposure_fraction"],
            "earliest_eta_hours": zone["earliest_eta_hours"],
            "consequence_weight": zone["consequence_weight"],
            "priority_rank": (
                triggered[0]["priority_rank"] if triggered else None
            ),
            "triggered_rules": [rule["rule_id"] for rule in triggered],
            "recommended_actions": list(dict.fromkeys(actions)),
            "status": "action_recommended" if triggered else "monitor",
        })

    queue.sort(
        key=lambda item: (
            item["priority_rank"] is None,
            item["priority_rank"] if item["priority_rank"] is not None else 0,
        )
    )

    return {
        "response_queue": queue,
        "interpretation": (
            "Recommendations come from configured rules and scenario "
            "forecasts; they are decision support, not operational orders."
        ),
    }


def main():
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: python -m backend.environment.response "
            "scenarios/response_demo.json"
        )

    path = Path(sys.argv[1])
    case = json.loads(path.read_text(encoding="utf-8-sig"))
    result = build_response_queue(
        case["impact_forecast"],
        case["policy"],
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()