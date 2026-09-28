import json
import sys
from pathlib import Path

from backend.environment.impact import forecast_hypothetical_impact
from backend.environment.opportunity import calculate_spill_opportunity
from backend.environment.uncertainty import calculate_data_uncertainty
from backend.environment.pre_spill import rank_surveillance_candidates


def evaluate_candidate(candidate):
    opportunity = calculate_spill_opportunity(
        candidate["opportunity"]["signals"],
        candidate["opportunity"]["weights"],
    )
    uncertainty = calculate_data_uncertainty(
        candidate["uncertainty"]["signals"],
        candidate["uncertainty"]["weights"],
    )
    impact = forecast_hypothetical_impact(candidate["impact_case"])

    behavior_index = candidate["behavior_index"]
    spill_opportunity = opportunity["spill_opportunity"]
    data_uncertainty = uncertainty["data_uncertainty"]
    impact_index = impact["impact_index"]

    components = (
        behavior_index,
        spill_opportunity,
        data_uncertainty,
        impact_index,
    )
    if any(not 0.0 <= value <= 1.0 for value in components):
        raise ValueError(
            f"{candidate['mmsi']}: every priority component must be in [0, 1]"
        )

    incident_proxy = behavior_index * spill_opportunity
    priority_index = incident_proxy * impact_index * data_uncertainty

    return {
        "mmsi": candidate["mmsi"],
        "behavior_index": behavior_index,
        "spill_opportunity": spill_opportunity,
        "potential_impact_index": impact_index,
        "data_uncertainty": data_uncertainty,
        "incident_proxy": incident_proxy,
        "priority_index": priority_index,
        "impact_forecast": impact,
        "score_meaning": (
            "Prototype surveillance ranking index; not a spill probability "
            "or attribution score."
        ),
    }


def main():
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: python -m backend.environment.queue_smoke_test "
            "scenarios/surveillance_demo.json"
        )

    scenario_path = Path(sys.argv[1])
    scenario = json.loads(scenario_path.read_text(encoding="utf-8-sig"))

    evaluated = [
        evaluate_candidate(candidate)
        for candidate in scenario["candidates"]
    ]
    queue = rank_surveillance_candidates(evaluated)

    print(json.dumps({
        "scenario_label": scenario.get("scenario_label", "UNLABELLED"),
        "queue": queue,
    }, indent=2))


if __name__ == "__main__":
    main()