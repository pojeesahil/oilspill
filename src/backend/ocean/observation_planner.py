import json
import math
import sys
from pathlib import Path


def _centroid(points, weights):
    x = y = z = 0.0

    for point, weight in zip(points, weights):
        lat = math.radians(point["lat"])
        lon = math.radians(point["lon"])
        x += weight * math.cos(lat) * math.cos(lon)
        y += weight * math.cos(lat) * math.sin(lon)
        z += weight * math.sin(lat)

    magnitude = math.sqrt(x * x + y * y + z * z)
    if magnitude == 0:
        raise ValueError("Cannot calculate centroid for opposing positions")

    return {
        "lat": math.degrees(math.atan2(z, math.sqrt(x * x + y * y))),
        "lon": math.degrees(math.atan2(y, x)),
    }


def _distance_m(a, b, earth_radius_m):
    lat1, lat2 = math.radians(a["lat"]), math.radians(b["lat"])
    d_lat = math.radians(b["lat"] - a["lat"])
    d_lon = math.radians(b["lon"] - a["lon"])

    value = (
        math.sin(d_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(d_lon / 2) ** 2
    )
    return 2 * earth_radius_m * math.asin(math.sqrt(min(1.0, value)))


def rank_observation_windows(case):
    settings = case["settings"]
    earth_radius_m = settings["earth_radius_m"]
    measurement_sigma_m = settings["measurement_sigma_m"]

    if earth_radius_m <= 0 or measurement_sigma_m < 0:
        raise ValueError("Invalid earth radius or observation uncertainty")

    ranked = []

    for window in case["candidate_observation_windows"]:
        hypotheses = window["hypotheses"]
        if len(hypotheses) < 2:
            raise ValueError("Each window needs at least two hypotheses")

        prior_total = sum(item["prior_weight"] for item in hypotheses)
        if prior_total <= 0:
            raise ValueError("Hypothesis prior weights must sum to a positive value")

        centers = []
        within_variance = 0.0

        for hypothesis in hypotheses:
            prior = hypothesis["prior_weight"] / prior_total
            samples = hypothesis["samples"]

            if prior < 0 or not samples:
                raise ValueError("Priors must be non-negative and samples non-empty")

            center = _centroid(
                samples,
                [1.0 / len(samples)] * len(samples),
            )

            squared_spread = sum(
                _distance_m(sample, center, earth_radius_m) ** 2
                for sample in samples
            ) / len(samples)

            within_variance += prior * squared_spread
            centers.append({
                "hypothesis_id": hypothesis["hypothesis_id"],
                "prior_weight": prior,
                "center": center,
                "rms_spread_m": math.sqrt(squared_spread),
            })

        global_center = _centroid(
            [item["center"] for item in centers],
            [item["prior_weight"] for item in centers],
        )

        between_variance = sum(
            item["prior_weight"]
            * _distance_m(item["center"], global_center, earth_radius_m) ** 2
            for item in centers
        )

        between_rms = math.sqrt(between_variance)
        within_rms = math.sqrt(within_variance)
        denominator = between_rms + within_rms + measurement_sigma_m
        separation_score = between_rms / denominator if denominator else 0.0

        ranked.append({
            "time": window["time"],
            "separation_score": separation_score,
            "predicted_regions": centers,
            "interpretation": (
                "Higher means the hypotheses predict more separated regions "
                "relative to forecast spread and observation uncertainty."
            ),
        })

    ranked.sort(key=lambda item: item["separation_score"], reverse=True)

    return {
        "recommended_observation_window": ranked[0] if ranked else None,
        "ranked_windows": ranked,
        "score_meaning": (
            "Synthetic simulation output. Heuristic forecast-separation score; "
            "not a formal information gain, satellite scheduling guarantee, or probability."
        ),
    }


def main():
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: python -m backend.ocean.observation_planner "
            "scenarios/observation_plan_demo.json"
        )

    path = Path(sys.argv[1])
    case = json.loads(path.read_text(encoding="utf-8-sig"))
    print(json.dumps(rank_observation_windows(case), indent=2))


if __name__ == "__main__":
    main()