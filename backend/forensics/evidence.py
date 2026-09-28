import json
import sys
from pathlib import Path

from backend.forensics.counterfactual import evaluate_counterfactuals


def build_hypothesis_report(counterfactual_result, behavior_context=None):
    behavior_context = behavior_context or {}
    threshold = counterfactual_result["threshold_used"]
    hypotheses = []

    for index, candidate in enumerate(counterfactual_result["candidates"], start=1):
        fraction = candidate["physical_consistency_fraction"]

        if fraction is None:
            evidence = [{
                "type": "counterfactual_centroid_reachability",
                "direction": "insufficient_data",
                "message": "No candidate release points fell within the configured time window.",
            }]
            status = "unresolved_insufficient_data"
        elif fraction >= threshold:
            evidence = [{
                "type": "counterfactual_centroid_reachability",
                "direction": "supports_physical_feasibility",
                "observed_fraction": fraction,
                "configured_threshold": threshold,
                "message": (
                    f"{candidate['compatible_simulations']} of "
                    f"{candidate['total_simulations']} simulations reached "
                    "the configured centroid radius."
                ),
            }]
            status = "physically_feasible_under_configured_test"
        else:
            evidence = [{
                "type": "counterfactual_centroid_reachability",
                "direction": "does_not_meet_configured_test",
                "observed_fraction": fraction,
                "configured_threshold": threshold,
                "message": (
                    "The simulated endpoint match fraction is below the "
                    "scenario's configured threshold."
                ),
            }]
            status = "not_supported_by_configured_test"

        for release in candidate.get("release_hypotheses", []):
            release_fraction = release["ensemble_consistency"]
            evidence.append({
                "type": "release_time_consistency",
                "direction": (
                    "supports_physical_feasibility"
                    if release_fraction >= threshold
                    else "does_not_meet_configured_test"
                ),
                "release_time": release["release_time"],
                "observed_fraction": release_fraction,
                "configured_threshold": threshold,
                "message": (
                    f"At this release time, {release_fraction:.1%} of "
                    "simulations matched the configured centroid radius."
                ),
            })

        hypotheses.append({
            "hypothesis": f"H{index}: discharge associated with {candidate['mmsi']}",
            "mmsi": candidate["mmsi"],
            "status": status,
            "evidence": evidence,
            "surveillance_context": {
                **behavior_context.get(candidate["mmsi"], {}),
                "use": (
                    "Pre-spill monitoring context only; not counted as "
                    "causal evidence in this report."
                ),
            },
        })

    source_assessment = counterfactual_result["source_assessment"]
    if source_assessment == "none_of_known_candidates_met_configured_threshold":
        unknown_status = "supported_by_configured_test"
        unknown_evidence = [{
            "direction": "supports_unknown_source_review",
            "message": (
                "No known AIS candidate met the configured centroid "
                "consistency threshold."
            ),
        }]
    elif source_assessment == "insufficient_candidate_tracks_in_time_window":
        unknown_status = "unresolved_insufficient_data"
        unknown_evidence = [{
            "direction": "insufficient_data",
            "message": (
                "Candidate AIS tracks did not provide enough release points "
                "inside the configured time window."
            ),
        }]
    else:
        unknown_status = "retained_as_alternative"
        unknown_evidence = [{
            "direction": "unresolved",
            "message": (
                "Known candidates met the configured test, but this does "
                "not rule out an untracked or non-AIS source."
            ),
        }]

    hypotheses.append({
        "hypothesis": "Unknown or untracked source",
        "status": unknown_status,
        "evidence": unknown_evidence,
    })

    return {
        "hypotheses": hypotheses,
        "interpretation": (
            "Evidence describes physical consistency under the configured "
            "scenario. It is not guilt, legal attribution, or a calibrated "
            "probability of source identity."
        ),
    }


def main():
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: python -m backend.forensics.evidence "
            "scenarios/attribution_demo.json"
        )

    scenario_path = Path(sys.argv[1])
    scenario = json.loads(scenario_path.read_text(encoding="utf-8-sig"))

    counterfactual = evaluate_counterfactuals(scenario)
    report = build_hypothesis_report(
        counterfactual,
        scenario.get("behavior_context", {}),
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()