import json
import math
import sys
from pathlib import Path

from oilspill.api.backend.ocean.drift import parse_time


def _distance_m(lat1, lon1, lat2, lon2, earth_radius_m):
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lam = math.radians(lon2 - lon1)

    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2) ** 2
    )
    return 2 * earth_radius_m * math.asin(math.sqrt(min(1.0, a)))


def _weighted_centroid(points, weights):
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

    lat = math.degrees(math.atan2(z, math.sqrt(x * x + y * y)))
    lon = math.degrees(math.atan2(y, x))
    return {"lat": lat, "lon": lon}


def update_forecast(case):
    observation = case["observation"]
    particles = case["particles"]
    earth_radius_m = case["physics"]["earth_radius_m"]
    measurement_sigma_m = observation["measurement_sigma_m"]
    observed_time = parse_time(observation["time"])

    if measurement_sigma_m <= 0:
        raise ValueError("measurement_sigma_m must be positive")
    if not particles:
        raise ValueError("Provide at least one forecast particle")

    log_weights = []
    residuals = []
    future_paths = []

    for particle in particles:
        prior_weight = float(particle["prior_weight"])
        if not math.isfinite(prior_weight) or prior_weight < 0:
            raise ValueError("prior_weight must be finite and non-negative")

        predicted = particle["predicted_at_observation"]
        residual = _distance_m(
            predicted["lat"],
            predicted["lon"],
            observation["lat"],
            observation["lon"],
            earth_radius_m,
        )
        residuals.append(residual)

        if prior_weight == 0:
            log_weight = float("-inf")
        else:
            # Gaussian observation likelihood, using scenario-supplied sigma.
            log_weight = (
                math.log(prior_weight)
                - 0.5 * (residual / measurement_sigma_m) ** 2
            )
        log_weights.append(log_weight)

        path_by_time = {}
        for point in particle["future_path"]:
            point_time = parse_time(point["time"])
            if point_time <= observed_time:
                raise ValueError(
                    "future_path points must be later than the observation"
                )
            key = point_time.isoformat()
            if key in path_by_time:
                raise ValueError(f"Duplicate forecast time: {key}")
            path_by_time[key] = point
        future_paths.append(path_by_time)

    max_log_weight = max(log_weights)
    if not math.isfinite(max_log_weight):
        raise ValueError("All particle prior weights are zero")

    unnormalized = [
        math.exp(value - max_log_weight) for value in log_weights
    ]
    weight_sum = sum(unnormalized)
    posterior_weights = [value / weight_sum for value in unnormalized]

    time_sets = [set(path) for path in future_paths]
    if time_sets and any(times != time_sets[0] for times in time_sets[1:]):
        raise ValueError("Every particle must have the same future forecast times")

    corrected_forecast = []
    for time_key in sorted(time_sets[0]) if time_sets else []:
        positions = [path[time_key] for path in future_paths]
        center = _weighted_centroid(positions, posterior_weights)
        corrected_forecast.append({
            "time": time_key,
            **center,
        })

    hypothesis_weights = {}
    updated_particles = []

    for index, particle in enumerate(particles):
        hypothesis_id = particle["hypothesis_id"]
        hypothesis_weights[hypothesis_id] = (
            hypothesis_weights.get(hypothesis_id, 0.0)
            + posterior_weights[index]
        )
        updated_particles.append({
            "particle_id": particle.get("particle_id", str(index)),
            "hypothesis_id": hypothesis_id,
            "observation_residual_m": round(residuals[index], 1),
            "posterior_weight": posterior_weights[index],
        })

    effective_sample_size = 1.0 / sum(
        weight * weight for weight in posterior_weights
    )

    return {
        "posterior_hypothesis_weights": hypothesis_weights,
        "particle_updates": updated_particles,
        "effective_sample_size": effective_sample_size,
        "corrected_forecast": corrected_forecast,
        "score_meaning": (
            "Synthetic simulation output. Forecast particles were reweighted "
            "against the supplied observation and measurement uncertainty. "
            "Results depend on the configured model and are not validated probabilities."
        ),
    }


def main():
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: python -m backend.ocean.forecast_update "
            "scenarios/forecast_update_demo.json"
        )

    path = Path(sys.argv[1])
    case = json.loads(path.read_text(encoding="utf-8-sig"))
    print(json.dumps(update_forecast(case), indent=2))


if __name__ == "__main__":
    main()