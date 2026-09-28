from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import math
import random


@dataclass(frozen=True)
class DriftForcing:
    current_east_mps: float
    current_north_mps: float
    wind_east_mps: float
    wind_north_mps: float
    current_uncertainty_mps: float
    wind_uncertainty_mps: float


@dataclass(frozen=True)
class DriftConfig:
    earth_radius_m: float
    step_seconds: float
    windage: float
    diffusion_m2ps: float
    longitude_cosine_floor: float


def parse_time(value):
    if isinstance(value, datetime):
        result = value
    else:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))

    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)

    return result


def move_position(lat, lon, east_m, north_m, config):
    cos_lat = math.cos(math.radians(lat))

    if abs(cos_lat) < config.longitude_cosine_floor:
        raise ValueError("Longitude movement is unstable near the poles")

    new_lat = lat + math.degrees(north_m / config.earth_radius_m)
    new_lon = lon + math.degrees(
        east_m / (config.earth_radius_m * cos_lat)
    )

    if not -90 <= new_lat <= 90:
        raise ValueError("Simulation moved outside valid latitude range")

    return new_lat, new_lon


def simulate_drift(
    lat,
    lon,
    start_time,
    duration_hours,
    forcing,
    config,
    direction,
    seed,
):
    """Run a constant-forcing prototype trajectory forward or backward."""
    if direction not in (-1, 1):
        raise ValueError("direction must be 1 or -1")
    if duration_hours < 0:
        raise ValueError("duration_hours cannot be negative")
    if config.step_seconds <= 0:
        raise ValueError("step_seconds must be positive")
    if config.earth_radius_m <= 0:
        raise ValueError("earth_radius_m must be positive")
    if config.diffusion_m2ps < 0:
        raise ValueError("diffusion_m2ps cannot be negative")

    rng = random.Random(seed)
    timestamp = parse_time(start_time)
    remaining_seconds = duration_hours * 3600

    points = [{"time": timestamp.isoformat(), "lat": lat, "lon": lon}]

    while remaining_seconds > 0:
        dt = min(config.step_seconds, remaining_seconds)
        remaining_seconds -= dt

        east_velocity = (
            forcing.current_east_mps
            + config.windage * forcing.wind_east_mps
        )
        north_velocity = (
            forcing.current_north_mps
            + config.windage * forcing.wind_north_mps
        )

        noise_scale = math.sqrt(2 * config.diffusion_m2ps * dt)
        east_step = direction * east_velocity * dt + rng.gauss(0, noise_scale)
        north_step = direction * north_velocity * dt + rng.gauss(0, noise_scale)

        lat, lon = move_position(lat, lon, east_step, north_step, config)
        timestamp += timedelta(seconds=direction * dt)

        points.append({
            "time": timestamp.isoformat(),
            "lat": lat,
            "lon": lon,
        })

    return points


def _quantile(values, q):
    if not 0 <= q <= 1:
        raise ValueError("Quantiles must be between 0 and 1")

    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    lower = math.floor(position)
    upper = math.ceil(position)
    fraction = position - lower

    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def monte_carlo_hindcast(
    observed_lat,
    observed_lon,
    observed_time,
    min_hours_before,
    max_hours_before,
    run_count,
    forcing,
    config,
    lower_quantile,
    upper_quantile,
    seed,
):
    """Sample possible release origins by perturbing forcing and release time."""
    if run_count < 1:
        raise ValueError("run_count must be at least 1")
    if min_hours_before < 0 or max_hours_before < min_hours_before:
        raise ValueError("Invalid release-time range")
    if lower_quantile >= upper_quantile:
        raise ValueError("lower_quantile must be below upper_quantile")

    rng = random.Random(seed)
    origins = []

    for run_index in range(run_count):
        duration = rng.uniform(min_hours_before, max_hours_before)

        sampled_forcing = DriftForcing(
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

        track = simulate_drift(
            observed_lat,
            observed_lon,
            observed_time,
            duration,
            sampled_forcing,
            config,
            direction=-1,
            seed=seed + run_index,
        )

        origin = track[-1]
        origins.append({
            "lat": origin["lat"],
            "lon": origin["lon"],
            "hours_before": duration,
        })

    return {
        "run_count": run_count,
        "origins": origins,
        "bounds": {
            "lat": [
                _quantile(
                    [point["lat"] for point in origins],
                    lower_quantile,
                ),
                _quantile(
                    [point["lat"] for point in origins],
                    upper_quantile,
                ),
            ],
            "lon": [
                _quantile(
                    [point["lon"] for point in origins],
                    lower_quantile,
                ),
                _quantile(
                    [point["lon"] for point in origins],
                    upper_quantile,
                ),
            ],
        },
    }