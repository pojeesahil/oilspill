"""Scenario-based ensemble forecast of hypothetical spill exposure.

Inputs (including physics settings and random seed) come from the scenario JSON.
GeoJSON ecosystem coordinates must use [longitude, latitude].
"""

import math
import random


def _point_in_ring(lon, lat, ring):
    """Ray-casting test; ring coordinates are [longitude, latitude]."""
    inside = False
    j = len(ring) - 1

    for i, point in enumerate(ring):
        xi, yi = point[0], point[1]
        xj, yj = ring[j][0], ring[j][1]

        if (yi > lat) != (yj > lat):
            crossing_lon = (xj - xi) * (lat - yi) / (yj - yi) + xi
            if lon < crossing_lon:
                inside = not inside
        j = i

    return inside


def _point_in_geometry(lon, lat, geometry):
    """Support GeoJSON Polygon and MultiPolygon geometries."""
    if geometry["type"] == "Polygon":
        polygons = [geometry["coordinates"]]
    elif geometry["type"] == "MultiPolygon":
        polygons = geometry["coordinates"]
    else:
        raise ValueError("Ecosystem zones must be Polygon or MultiPolygon")

    for polygon in polygons:
        if not polygon or not _point_in_ring(lon, lat, polygon[0]):
            continue
        # A point inside a hole is outside the ecosystem zone.
        if not any(_point_in_ring(lon, lat, hole) for hole in polygon[1:]):
            return True

    return False


def forecast_hypothetical_impact(case):
    """Run a configured forward ensemble from one hypothetical release point."""
    release = case["release"]
    cfg = case["forecast"]
    zones = case["ecosystem_zones"]["features"]

    required = (
        "ensemble_runs", "random_seed", "duration_hours", "step_minutes",
        "current_east_mps", "current_north_mps",
        "current_sd_mps", "wind_east_mps", "wind_north_mps",
        "wind_sd_mps", "windage_fraction", "diffusion_m2_s",
    )
    missing = [key for key in required if key not in cfg]
    if missing:
        raise ValueError(f"Missing forecast settings: {', '.join(missing)}")

    if cfg["ensemble_runs"] <= 0 or cfg["step_minutes"] <= 0:
        raise ValueError("ensemble_runs and step_minutes must be positive")
    if cfg["duration_hours"] <= 0 or cfg["diffusion_m2_s"] < 0:
        raise ValueError("duration_hours must be positive; diffusion cannot be negative")

    rng = random.Random(cfg["random_seed"])
    step_seconds = cfg["step_minutes"] * 60
    steps = math.ceil(cfg["duration_hours"] * 60 / cfg["step_minutes"])
    zone_hits = {i: 0 for i in range(len(zones))}
    zone_etas = {i: [] for i in range(len(zones))}
    sample_path = []

    for run in range(cfg["ensemble_runs"]):
        lat = float(release["lat"])
        lon = float(release["lon"])
        path = []

        # Perturb forcing once per run; add configured diffusion at each step.
        current_e = rng.gauss(cfg["current_east_mps"], cfg["current_sd_mps"])
        current_n = rng.gauss(cfg["current_north_mps"], cfg["current_sd_mps"])
        wind_e = rng.gauss(cfg["wind_east_mps"], cfg["wind_sd_mps"])
        wind_n = rng.gauss(cfg["wind_north_mps"], cfg["wind_sd_mps"])

        hit_this_run = set()

        for step in range(steps + 1):
            hours = min(step * cfg["step_minutes"] / 60, cfg["duration_hours"])
            path.append({"hours": round(hours, 3), "lat": lat, "lon": lon})

            for i, feature in enumerate(zones):
                if i not in hit_this_run and _point_in_geometry(
                    lon, lat, feature["geometry"]
                ):
                    hit_this_run.add(i)
                    zone_etas[i].append(hours)

            if step == steps:
                break

            # Drift = current + configured fraction of wind + random diffusion.
            east_m = (current_e + cfg["windage_fraction"] * wind_e) * step_seconds
            north_m = (current_n + cfg["windage_fraction"] * wind_n) * step_seconds
            diffusion_sd = math.sqrt(2 * cfg["diffusion_m2_s"] * step_seconds)
            east_m += rng.gauss(0, diffusion_sd)
            north_m += rng.gauss(0, diffusion_sd)

            lat += north_m / 111_320
            lon += east_m / (111_320 * max(abs(math.cos(math.radians(lat))), 1e-6))

        for i in hit_this_run:
            zone_hits[i] += 1

        if run == 0:
            sample_path = path

    zone_results = []
    weighted_exposure = 0.0
    total_weight = 0.0

    for i, feature in enumerate(zones):
        props = feature.get("properties", {})
        weight = float(props["consequence_weight"])
        probability = zone_hits[i] / cfg["ensemble_runs"]
        weighted_exposure += probability * weight
        total_weight += weight

        zone_results.append({
            "name": props.get("name", f"zone_{i}"),
            "exposure_fraction": round(probability, 4),
            "earliest_eta_hours": (
                round(min(zone_etas[i]), 2) if zone_etas[i] else None
            ),
            "consequence_weight": weight,
        })

    return {
        "impact_index": round(
            weighted_exposure / total_weight if total_weight else 0.0, 4
        ),
        "score_meaning": (
            "Prototype consequence index from configured scenario ensemble; "
            "not a validated spill probability or operational forecast."
        ),
        "ensemble_runs": cfg["ensemble_runs"],
        "zones": zone_results,
        "sample_trajectory": sample_path,
    }