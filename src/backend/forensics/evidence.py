import json
import sys
from pathlib import Path

from backend.forensics.counterfactual import evaluate_counterfactuals


def _metric_evidence(vector, vector_threshold):
    if vector is None:
        return [{
            "type": "physical_consistency_vector",
            "direction": "insufficient_data",
            "message": "No physical-consistency vector could be calculated.",
        }]

    score = vector.get("physical_consistency_score")
    if score is None:
        direction = "insufficient_data"
        message = "The composite physical-consistency score is unavailable."
    elif score >= vector_threshold:
        direction = "supports_configured_vector_test"
        message = (
            f"Composite geometry score {score:.3f} meets the configured "
            f"vector threshold {vector_threshold:.3f}. This is a prototype "
            "consistency index, not a probability or attribution finding."
        )
    else:
        direction = "does_not_meet_configured_vector_test"
        message = (
            f"Composite geometry score {score:.3f} is below the configured "
            f"vector threshold {vector_threshold:.3f}."
        )

    evidence = [{
        "type": "physical_consistency_vector",
        "direction": direction,
        "observed_score": score,
        "configured_threshold": vector_threshold,
        "message": message,
    }]

    labels = {
        "centroid_fraction": "Centroid match fraction",
        "polygon_support_fraction": "Footprint polygon support fraction",
        "area_similarity": "Endpoint-envelope versus footprint area similarity",
        "orientation_similarity": "Orientation similarity",
    }
    for metric, label in labels.items():
        value = vector.get(metric)
        if value is None:
            why = vector.get("score_components_excluded", {}).get(
                metric, "Metric is indeterminate for this geometry."
            )
            evidence.append({
                "type": f"vector_metric:{metric}",
                "direction": "indeterminate_or_excluded",
                "observed_value": None,
                "message": f"{label}: unavailable; {why}",
            })
        else:
            evidence.append({
                "type": f"vector_metric:{metric}",
                "direction": "descriptive_component",
                "observed_value": value,
                "included_in_composite": metric in vector.get(
                    "score_components_used", []
                ),
                "message": f"{label}: {value:.3f}.",
            })
    evidence.append({
        "type": "vector_metric_accounting",
        "direction": "explanation",
        "message": vector.get("interpretation", ""),
    })
    return evidence


def build_hypothesis_report(counterfactual_result, behavior_context=None):
    behavior_context = behavior_context or {}
    centroid_threshold = counterfactual_result["threshold_used"]
    vector_threshold = counterfactual_result["vector_threshold_used"]
    hypotheses = []
    known_candidate_passed_both = False
    sufficient_candidates = False

    for index, candidate in enumerate(counterfactual_result["candidates"], start=1):
        fraction = candidate.get("physical_consistency_fraction")
        vector_score = candidate.get("physical_consistency_score")
        centroid_available = fraction is not None
        vector_available = vector_score is not None
        sufficient_candidates |= centroid_available or vector_available
        centroid_pass = centroid_available and fraction >= centroid_threshold
        vector_pass = vector_available and vector_score >= vector_threshold
        known_candidate_passed_both |= centroid_pass and vector_pass

        evidence = []
        if not centroid_available:
            evidence.append({
                "type": "counterfactual_centroid_reachability",
                "direction": "insufficient_data",
                "message": "No candidate release points fell within the configured time window.",
            })
        else:
            evidence.append({
                "type": "counterfactual_centroid_reachability",
                "direction": "supports_configured_centroid_test" if centroid_pass else "does_not_meet_configured_centroid_test",
                "observed_fraction": fraction,
                "configured_threshold": centroid_threshold,
                "message": (
                    f"{candidate['compatible_simulations']} of {candidate['total_simulations']} "
                    f"synthetic simulations reached the configured centroid radius "
                    f"(fraction {fraction:.3f}; threshold {centroid_threshold:.3f})."
                ),
            })

        evidence.extend(_metric_evidence(
            candidate.get("physical_consistency_vector"), vector_threshold
        ))
        for release in candidate.get("release_hypotheses", []):
            release_fraction = release.get("ensemble_consistency")
            evidence.append({
                "type": "release_time_consistency",
                "direction": "supports_configured_centroid_test" if release_fraction >= centroid_threshold else "does_not_meet_configured_centroid_test",
                "release_time": release["release_time"],
                "observed_fraction": release_fraction,
                "configured_threshold": centroid_threshold,
                "message": (
                    f"At hypothetical release time {release['release_time']}, "
                    f"{release_fraction:.1%} of synthetic endpoints matched "
                    "the configured centroid radius. This is not an observed discharge."
                ),
            })

        if centroid_pass and vector_pass:
            status = "meets_both_configured_physical_consistency_tests"
        elif centroid_pass:
            status = "centroid_test_only_vector_test_not_met_or_unavailable"
        elif vector_pass:
            status = "vector_test_only_centroid_test_not_met_or_unavailable"
        elif not centroid_available and not vector_available:
            status = "unresolved_insufficient_data"
        else:
            status = "does_not_meet_configured_physical_consistency_tests"

        hypotheses.append({
            "hypothesis": f"H{index}: discharge associated with {candidate['mmsi']}",
            "mmsi": candidate["mmsi"],
            "status": status,
            "evidence": evidence,
            "surveillance_context": {
                **behavior_context.get(candidate["mmsi"], {}),
                "use": "Pre-spill monitoring context only; not counted as post-spill causal evidence.",
            },
        })

    centroid_assessment = counterfactual_result["source_assessment"]
    vector_assessment = counterfactual_result["vector_assessment"]
    if not sufficient_candidates:
        unknown_status = "unresolved_insufficient_data"
        unknown_message = "Candidate AIS tracks did not provide enough release points for either configured test."
    elif not known_candidate_passed_both:
        unknown_status = "supported_as_alternative_for_review"
        unknown_message = (
            "No known AIS candidate met both configured centroid and vector "
            "tests. Keep unknown or untracked sources in the investigation; "
            "this does not establish that the source was unknown."
        )
    else:
        unknown_status = "retained_as_alternative"
        unknown_message = (
            "At least one known candidate met both configured tests, but that "
            "does not rule out an untracked or non-AIS source."
        )

    hypotheses.append({
        "hypothesis": "Unknown or untracked source",
        "status": unknown_status,
        "evidence": [{
            "type": "none_of_known_candidates_assessment",
            "direction": "supports_unknown_source_review" if unknown_status == "supported_as_alternative_for_review" else "insufficient_data" if unknown_status == "unresolved_insufficient_data" else "unresolved_alternative",
            "centroid_assessment": centroid_assessment,
            "centroid_threshold": centroid_threshold,
            "vector_assessment": vector_assessment,
            "vector_threshold": vector_threshold,
            "message": unknown_message,
        }],
    })

    return {
        "scenario_label": "SYNTHETIC COUNTERFACTUAL ASSESSMENT",
        "hypotheses": hypotheses,
        "interpretation": (
            "Evidence describes synthetic physical-consistency tests under "
            "configured scenario settings. The scores are not calibrated "
            "probabilities, guilt scores, proof of identity, or legal attribution. "
            "Pre-spill surveillance context is kept separate from post-spill causal evidence."
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
