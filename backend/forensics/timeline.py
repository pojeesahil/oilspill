import json
import sys
from pathlib import Path

from backend.ocean.drift import parse_time


def build_investigation_timeline(case):
    events = []
    mmsi = case["mmsi"]

    for point in case.get("ais_timeline", []):
        reasons = point.get("reasons", [])
        events.append({
            "time": point["time"],
            "type": "ais_behavior_update",
            "title": "AIS behavior signal" if reasons else "AIS report",
            "details": reasons,
            "behavior_score": point.get("behavior_score"),
            "position": {
                "lat": point["lat"],
                "lon": point["lon"],
            },
            "evidence_role": (
                "Pre-spill surveillance context; not causal attribution evidence."
            ),
        })

    spill_time = case["observed_spill"]["time"]
    events.append({
        "time": spill_time,
        "type": "sar_spill_observation",
        "title": "Spill observed by SAR",
        "details": case["observed_spill"].get("description"),
        "evidence_role": "Observed incident evidence.",
    })

    counterfactual = case.get("counterfactual_result", {})
    threshold = counterfactual.get("threshold_used")

    for candidate in counterfactual.get("candidates", []):
        candidate_mmsi = candidate["mmsi"]

        for release in candidate.get("release_hypotheses", []):
            events.append({
                "time": release["release_time"],
                "type": "hypothetical_release_test",
                "title": f"Release-time hypothesis tested for {candidate_mmsi}",
                "consistency_fraction": release["ensemble_consistency"],
                "configured_threshold": threshold,
                "details": (
                    "This is a simulated release time, not an observed discharge."
                ),
                "evidence_role": "Counterfactual physical-consistency test.",
            })

    response = case.get("response_result", {})
    for zone in response.get("response_queue", []):
        for action in zone.get("recommended_actions", []):
            events.append({
                "time": spill_time,
                "type": "response_recommendation",
                "title": f"Recommendation for {zone['zone']}",
                "details": action,
                "priority_rank": zone.get("priority_rank"),
                "evidence_role": (
                    "Configured decision-support rule; not a recorded action."
                ),
            })

    events.sort(key=lambda event: parse_time(event["time"]))

    return {
        "mmsi": mmsi,
        "events": events,
        "interpretation": (
            "The timeline separates observed AIS/SAR events from simulated "
            "release hypotheses and suggested response actions."
        ),
    }


def main():
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: python -m backend.forensics.timeline "
            "scenarios/investigation_timeline_demo.json"
        )

    path = Path(sys.argv[1])
    case = json.loads(path.read_text(encoding="utf-8-sig"))
    print(json.dumps(build_investigation_timeline(case), indent=2))


if __name__ == "__main__":
    main()