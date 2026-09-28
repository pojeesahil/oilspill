import json
import math
import sys
from pathlib import Path

from backend.ocean.drift import parse_time


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


def _course_difference_deg(course_a, course_b):
    difference = abs(course_a - course_b) % 360
    return min(difference, 360 - difference)


def inspect_ais_integrity(case):
    cfg = case["settings"]
    earth_radius_m = cfg["earth_radius_m"]
    meters_per_nautical_mile = cfg["meters_per_nautical_mile"]
    seconds_per_hour = cfg["seconds_per_hour"]

    if earth_radius_m <= 0 or meters_per_nautical_mile <= 0 or seconds_per_hour <= 0:
        raise ValueError("Distance and time conversion values must be positive")

    events = []

    for vessel in case["tracks"]:
        points = sorted(vessel["points"], key=lambda p: parse_time(p["time"]))
        speed_limit = case["speed_limits_knots"].get(vessel["vessel_type"])

        for index in range(1, len(points)):
            previous = points[index - 1]
            current = points[index]

            elapsed = (
                parse_time(current["time"]) - parse_time(previous["time"])
            ).total_seconds()
            if elapsed <= 0:
                continue

            distance_m = _distance_m(
                previous["lat"], previous["lon"],
                current["lat"], current["lon"],
                earth_radius_m,
            )
            implied_knots = (
                distance_m / meters_per_nautical_mile
                * seconds_per_hour / elapsed
            )

            if speed_limit is not None and implied_knots > speed_limit:
                events.append({
                    "mmsi": vessel["mmsi"],
                    "type": "impossible_speed_jump",
                    "from_time": previous["time"],
                    "to_time": current["time"],
                    "implied_speed_knots": implied_knots,
                    "configured_vessel_limit_knots": speed_limit,
                    "interpretation": (
                        "Position-derived speed exceeds the configured vessel "
                        "limit; check AIS data and vessel classification."
                    ),
                })

            max_turn_interval = cfg["max_course_change_interval_seconds"]
            reversal_threshold = cfg["course_reversal_threshold_deg"]

            if (
                elapsed <= max_turn_interval
                and previous.get("cog_degrees") is not None
                and current.get("cog_degrees") is not None
            ):
                turn = _course_difference_deg(
                    previous["cog_degrees"],
                    current["cog_degrees"],
                )
                if turn >= reversal_threshold:
                    events.append({
                        "mmsi": vessel["mmsi"],
                        "type": "abrupt_course_change",
                        "from_time": previous["time"],
                        "to_time": current["time"],
                        "course_change_degrees": turn,
                        "interpretation": (
                            "Large course change over a short interval; "
                            "requires review and may reflect a turn or bad data."
                        ),
                    })

        # Look for a run of consecutive reports at effectively the same spot.
        run_start = 0
        for index in range(1, len(points) + 1):
            same_position = (
                index < len(points)
                and _distance_m(
                    points[index - 1]["lat"], points[index - 1]["lon"],
                    points[index]["lat"], points[index]["lon"],
                    earth_radius_m,
                ) <= cfg["frozen_coordinate_tolerance_m"]
            )

            if same_position:
                continue

            run_length = index - run_start
            if run_length >= cfg["frozen_minimum_points"]:
                events.append({
                    "mmsi": vessel["mmsi"],
                    "type": "repeated_frozen_coordinates",
                    "start_time": points[run_start]["time"],
                    "end_time": points[index - 1]["time"],
                    "repeated_points": run_length,
                    "interpretation": (
                        "Several reports remained within the configured "
                        "coordinate tolerance; check for a stationary vessel "
                        "or repeated/stale AIS data."
                    ),
                })
            run_start = index

    events.sort(
        key=lambda event: parse_time(
            event.get("from_time", event.get("start_time"))
        )
    )

    return {
        "events": events,
        "score_meaning": (
            "Configurable AIS data-integrity flags; not proof of spoofing, "
            "illegal activity, or intent."
        ),
    }


def main():
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: python -m backend.vessels.integrity "
            "scenarios/ais_integrity_demo.json"
        )

    path = Path(sys.argv[1])
    case = json.loads(path.read_text(encoding="utf-8-sig"))
    print(json.dumps(inspect_ais_integrity(case), indent=2))


if __name__ == "__main__":
    main()