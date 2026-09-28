import json
import math
import random
import sys
from pathlib import Path

from backend.forensics.physical_consistency import score_ensemble
from backend.ocean.drift import (
    DriftConfig,
    DriftForcing,
    parse_time,
    simulate_drift,
)


def _distance_m(lat1, lon1, lat2, lon2, earth_radius_m):
    """Haversine distance between two latitude/longitude points."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lam = math.radians(lon2 - lon1)

    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2) ** 2
    )
    return 2 * earth_radius_m * math.asin(
        math.sqrt(min(1.0, a))
    )


def _sample_forcing(forcing, rng):
    """Sample current and wind within scenario-supplied uncertainty."""
    return DriftForcing(
        current_east_mps=rng.gauss(
            forcing.current_east_mps,
            forcing.current_uncertainty_mps,
        ),
        current_north_mps=rng.gauss(
            forcing.current_north_mps,
            forcing.current_uncertainty_mps,
        ),
        wind_east_mps=rng.gauss(
            forcing.wind_east_mps,
            forcing.wind_uncertainty_mps,
        ),
        wind_north_mps=rng.gauss(
            forcing.wind_north_mps,
            forcing.wind_uncertainty_mps,
        ),
        current_uncertainty_mps=forcing.current_uncertainty_mps,
        wind_uncertainty_mps=forcing.wind_uncertainty_mps,
    )


def evaluate_counterfactuals(scenario):
    observed = scenario["observation"]
    settings = scenario["analysis"]
    config = DriftConfig(**scenario["drift_config"])
    base_forcing = DriftForcing(**scenario["forcing"])

    run_count = settings["run_count"]
    radius_m = settings["match_radius_m"]
    min_hours = settings["min_hours_before"]
    max_hours = settings["max_hours_before"]
    centroid_threshold = settings["minimum_consistency_fraction"]
    vector_threshold = settings["minimum_vector_score"]
    vector_weights = settings["vector_weights"]

    if run_count <= 0 or radius_m <= 0:
        raise ValueError("run_count and match_radius_m must be positive")
    if min_hours < 0 or max_hours < min_hours:
        raise ValueError("Invalid release-time window")
    if not 0.0 <= centroid_threshold <= 1.0:
        raise ValueError(
            "minimum_consistency_fraction must be in [0, 1]"
        )
    if not 0.0 <= vector_threshold <= 1.0:
        raise ValueError("minimum_vector_score must be in [0, 1]")
    if "footprint_geojson" not in observed:
        raise ValueError(
            "Add observation.footprint_geojson to the scenario"
        )

    observed_time = parse_time(observed["time"])
    centroid = observed["centroid"]
    footprint = observed["footprint_geojson"]
    results = []

    for candidate_index, candidate in enumerate(scenario["candidates"]):
        compatible = 0
        total = 0
        release_results = []
        sample_trajectory = None
        vector_weighted_sum = 0.0
        vector_endpoint_count = 0

        for point_index, ais_point in enumerate(candidate["track"]):
            release_time = parse_time(ais_point["time"])
            hours_before = (
                observed_time - release_time
            ).total_seconds() / 3600

            if not min_hours <= hours_before <= max_hours:
                continue

            release_compatible = 0
            release_endpoints = []

            for run_index in range(run_count):
                seed = (
                    settings["random_seed"]
                    + candidate_index * run_count * len(candidate["track"])
                    + point_index * run_count
                    + run_index
                )
                rng = random.Random(seed)
                sampled_forcing = _sample_forcing(base_forcing, rng)

                path = simulate_drift(
                    lat=ais_point["lat"],
                    lon=ais_point["lon"],
                    start_time=ais_point["time"],
                    duration_hours=hours_before,
                    forcing=sampled_forcing,
                    config=config,
                    direction=1,
                    seed=seed,
                )

                endpoint = path[-1]
                release_endpoints.append(endpoint)

                distance = _distance_m(
                    endpoint["lat"],
                    endpoint["lon"],
                    centroid["lat"],
                    centroid["lon"],
                    config.earth_radius_m,
                )

                if distance <= radius_m:
                    compatible += 1
                    release_compatible += 1

                total += 1

                if sample_trajectory is None:
                    sample_trajectory = path

            vector = score_ensemble(
                endpoints=release_endpoints,
                footprint_geojson=footprint,
                centroid=centroid,
                earth_radius_m=config.earth_radius_m,
                match_radius_m=radius_m,
                weights=vector_weights,
            )

            vector_weighted_sum += (
                vector["physical_consistency_score"]
                * len(release_endpoints)
            )
            vector_endpoint_count += len(release_endpoints)

            release_results.append({
                "release_time": ais_point["time"],
                "ensemble_consistency": (
                    release_compatible / run_count
                ),
                "simulations": run_count,
                "physical_consistency_vector": vector,
            })

        centroid_fraction = compatible / total if total else None
        vector_score = (
            vector_weighted_sum / vector_endpoint_count
            if vector_endpoint_count
            else None
        )

        # Summarize component metrics across release hypotheses. Indeterminate
        # components (notably orientation) remain null and are never implied
        # to have contributed to the composite score.
        component_names = (
            "centroid_fraction",
            "polygon_support_fraction",
            "area_similarity",
            "orientation_similarity",
        )
        aggregate_vector = None
        if release_results:
            aggregate_vector = {
                name: round(
                    sum(
                        release["physical_consistency_vector"][name]
                        for release in release_results
                        if release["physical_consistency_vector"].get(name) is not None
                    ) / max(1, sum(
                        release["physical_consistency_vector"].get(name) is not None
                        for release in release_results
                    )),
                    4,
                ) if any(
                    release["physical_consistency_vector"].get(name) is not None
                    for release in release_results
                ) else None
                for name in component_names
            }
            aggregate_vector.update({
                "physical_consistency_score": round(vector_score, 4),
                "score_components_used": sorted({
                    name
                    for release in release_results
                    for name in release["physical_consistency_vector"].get("score_components_used", [])
                }),
                "score_components_excluded": {
                    name: reason
                    for release in release_results
                    for name, reason in release["physical_consistency_vector"].get("score_components_excluded", {}).items()
                },
                "interpretation": (
                    "Candidate-level component values are unweighted means "
                    "across release-time vectors, ignoring indeterminate values. "
                    "The composite candidate score is endpoint-weighted. "
                    "Orientation contributes only where it was determinate and used."
                ),
            })

        results.append({
            "mmsi": candidate["mmsi"],
            "physical_consistency_fraction": centroid_fraction,
            "physical_consistency_score": (
                round(vector_score, 4)
                if vector_score is not None
                else None
            ),
            "physical_consistency_vector": aggregate_vector,
            "compatible_simulations": compatible,
            "total_simulations": total,
            "release_hypotheses": release_results,
            "sample_trajectory": sample_trajectory,
            "score_meaning": (
                "physical_consistency_fraction is the fraction of synthetic "
                "endpoints within the configured centroid radius. The vector "
                "score is a weighted geometry index using only determinate "
                "metrics with positive configured weights; orientation is "
                "excluded when indeterminate. Neither is a probability."
            ),
        })

    centroid_ranked = [
        item for item in results
        if item["physical_consistency_fraction"] is not None
    ]
    vector_ranked = [
        item for item in results
        if item["physical_consistency_score"] is not None
    ]

    ranked = sorted(
        vector_ranked,
        key=lambda item: (
            item["physical_consistency_score"],
            item["physical_consistency_fraction"] or 0.0,
        ),
        reverse=True,
    )

    if not centroid_ranked:
        source_assessment = (
            "insufficient_candidate_tracks_in_time_window"
        )
    elif all(
        item["physical_consistency_fraction"] < centroid_threshold
        for item in centroid_ranked
    ):
        source_assessment = (
            "none_of_known_candidates_met_configured_centroid_threshold"
        )
    else:
        source_assessment = (
            "one_or_more_candidates_met_configured_centroid_threshold"
        )

    if not vector_ranked:
        vector_assessment = (
            "insufficient_candidate_tracks_for_vector_comparison"
        )
    elif all(
        item["physical_consistency_score"] < vector_threshold
        for item in vector_ranked
    ):
        vector_assessment = (
            "none_of_known_candidates_met_configured_vector_threshold"
        )
    else:
        vector_assessment = (
            "one_or_more_candidates_met_configured_vector_threshold"
        )

    return {
        "source_assessment": source_assessment,
        "threshold_used": centroid_threshold,
        "vector_assessment": vector_assessment,
        "vector_threshold_used": vector_threshold,
        "candidates": ranked,
        "score_meaning": (
            "Centroid consistency is a configured simulation fraction, not "
            "a probability of guilt. The vector score compares simulated "
            "endpoint envelopes with the supplied footprint and is a "
            "prototype geometry proxy, not legal attribution."
        ),
    }


def main():
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: python -m backend.forensics.counterfactual "
            "scenarios/attribution_demo.json"
        )

    path = Path(sys.argv[1])
    scenario = json.loads(path.read_text(encoding="utf-8-sig"))
    print(json.dumps(evaluate_counterfactuals(scenario), indent=2))


if __name__ == "__main__":
    main()