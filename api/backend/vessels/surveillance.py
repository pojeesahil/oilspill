from math import asin, cos, exp, radians, sin, sqrt
from oilspill.api.backend.ocean.drift import parse_time


def _clamp(value):
    return max(0.0, min(1.0, value))


def _scale(value, start, full):
    if full <= start:
        raise ValueError("Each score range must have full > start")
    return _clamp((value - start) / (full - start))


def _angle_difference(a, b):
    difference = abs((a - b) % 360)
    return min(difference, 360 - difference)


def _distance_m(a, b, earth_radius_m):
    lat1, lon1 = radians(a["lat"]), radians(a["lon"])
    lat2, lon2 = radians(b["lat"]), radians(b["lon"])
    dlat, dlon = lat2 - lat1, lon2 - lon1

    value = (
        sin(dlat / 2) ** 2
        + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    )
    return 2 * earth_radius_m * asin(sqrt(value))


def analyze_track(case):
    vessel = case["vessel"]
    settings = case["settings"]
    points = sorted(case["ais_points"], key=lambda p: parse_time(p["time"]))

    if len(points) < 2:
        raise ValueError("At least two AIS points are required")

    vessel_type = vessel["type"]
    context = vessel["operating_context"]
    baseline = case["contextual_baselines"][vessel_type][context]
    weights = settings["weights"]

    if not weights or sum(weights.values()) <= 0:
        raise ValueError("Feature weights must have a positive sum")

    risk = settings["initial_risk"]
    loiter_seconds = 0.0
    timeline = []

    for index, point in enumerate(points):
        signals = {
            "speed_deviation": 0.0,
            "loitering": 0.0,
            "ais_gap": 0.0,
            "kinematic": 0.0,
            "route_deviation": 0.0,
            "course_change": 0.0,
        }
        elapsed_seconds = 0.0

        if index > 0:
            previous = points[index - 1]
            elapsed_seconds = (
                parse_time(point["time"]) - parse_time(previous["time"])
            ).total_seconds()

            if elapsed_seconds <= 0:
                raise ValueError("AIS timestamps must be strictly increasing")

            # Older risk fades as time passes.
            risk *= exp(
                -settings["risk_decay_per_hour"] * elapsed_seconds / 3600
            )

            # Speed is compared with the vessel's type and location context.
            speed_z = abs(
                point["sog_knots"] - baseline["speed_mean_knots"]
            ) / baseline["speed_std_knots"]

            signals["speed_deviation"] = _scale(
                speed_z,
                settings["speed_z_score"]["start"],
                settings["speed_z_score"]["full"],
            )

            # Do not treat a long AIS silence as continuous loitering.
            loiter_elapsed = min(
                elapsed_seconds,
                settings["loitering"]["max_interval_seconds"],
            )

            if point["sog_knots"] <= settings["loitering"]["speed_limit_knots"]:
                loiter_seconds += loiter_elapsed
            else:
                loiter_seconds = 0.0

            signals["loitering"] = _scale(
                loiter_seconds,
                settings["loitering"]["duration_start_seconds"],
                settings["loitering"]["duration_full_seconds"],
            )

            signals["ais_gap"] = _scale(
                elapsed_seconds,
                settings["ais_gap"]["duration_start_seconds"],
                settings["ais_gap"]["duration_full_seconds"],
            )

            distance = _distance_m(
                previous, point, settings["earth_radius_m"]
            )
            implied_speed_knots = (
                distance / elapsed_seconds
                / settings["meters_per_second_per_knot"]
            )
            speed_ratio = implied_speed_knots / baseline["max_speed_knots"]

            signals["kinematic"] = _scale(
                speed_ratio,
                settings["kinematic"]["speed_ratio_start"],
                settings["kinematic"]["speed_ratio_full"],
            )

            route_difference = _angle_difference(
                point["cog_deg"],
                point["expected_route_bearing_deg"],
            )
            signals["route_deviation"] = _scale(
                route_difference,
                settings["route_deviation"]["degrees_start"],
                settings["route_deviation"]["degrees_full"],
            )

            turn_rate = (
                _angle_difference(point["cog_deg"], previous["cog_deg"])
                / (elapsed_seconds / 60)
            )
            signals["course_change"] = _scale(
                turn_rate,
                settings["course_change"]["degrees_per_minute_start"],
                settings["course_change"]["degrees_per_minute_full"],
            )

            weighted_event = sum(
                weights[name] * signals[name] for name in weights
            ) / sum(weights.values())

            # Accumulate current evidence while retaining residual older risk.
            risk = _clamp(
                risk
                + settings["evidence_gain"]
                * weighted_event
                * (1 - risk)
            )

        threshold = settings["reason_display_threshold"]
        timeline.append({
            "time": point["time"],
            "lat": point["lat"],
            "lon": point["lon"],
            "behavior_score": risk,
            "signals": signals,
            "reasons": [
                name for name, value in signals.items()
                if value >= threshold
            ],
        })

    return {
        "mmsi": vessel["mmsi"],
        "vessel_type": vessel_type,
        "operating_context": context,
        "behavior_score": timeline[-1]["behavior_score"],
        "score_meaning": "Prototype surveillance signal; not a spill probability or guilt score.",
        "timeline": timeline,
    }