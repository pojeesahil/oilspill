import json
import math
import sys
from pathlib import Path

from backend.ocean.drift import DriftConfig, move_position, parse_time


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


def assess_gap_detections(case):
    settings = case["settings"]
    physics = DriftConfig(**case["physics"])

    max_gap_hours = settings["max_gap_hours"]
    knots_to_mps = settings["knots_to_mps"]
    base_radius_m = settings["base_corridor_radius_m"]
    growth_mps = settings["corridor_growth_mps"]

    if max_gap_hours <= 0 or knots_to_mps <= 0:
        raise ValueError("max_gap_hours and knots_to_mps must be positive")
    if base_radius_m < 0 or growth_mps < 0:
        raise ValueError("Corridor radius and growth rate cannot be negative")

    possible_matches = []

    for report_index, vessel in enumerate(case["ais_gap_reports"]):
        last_report = vessel["last_report"]
        last_time = parse_time(last_report["time"])
        speed_knots = float(last_report["sog_knots"])
        course_degrees = float(last_report["cog_degrees"])

        if speed_knots < 0:
            raise ValueError(f"{vessel['mmsi']}: speed cannot be negative")
        if not 0.0 <= course_degrees <= 360.0:
            raise ValueError(f"{vessel['mmsi']}: course must be between 0 and 360")

        gap_end = vessel.get("gap_end_time")
        gap_end_time = parse_time(gap_end) if gap_end else None

        for detection_index, detection in enumerate(case["sar_detections"]):
            detection_time = parse_time(detection["time"])
            elapsed_seconds = (detection_time - last_time).total_seconds()

            # Dead reckoning only projects forward, and only for the
            # configured maximum gap duration.
            if elapsed_seconds <= 0:
                continue
            if elapsed_seconds > max_gap_hours * 3600:
                continue
            if gap_end_time and detection_time > gap_end_time:
                continue

            speed_mps = speed_knots * knots_to_mps
            course = math.radians(course_degrees)

            east_m = speed_mps * math.sin(course) * elapsed_seconds
            north_m = speed_mps * math.cos(course) * elapsed_seconds

            predicted_lat, predicted_lon = move_position(
                last_report["lat"],
                last_report["lon"],
                east_m,
                north_m,
                physics,
            )

            distance = _distance_m(
                predicted_lat,
                predicted_lon,
                detection["lat"],
                detection["lon"],
                physics.earth_radius_m,
            )

            corridor_radius = base_radius_m + growth_mps * elapsed_seconds

            possible_matches.append({
                "report_index": report_index,
                "detection_index": detection_index,
                "vessel": vessel,
                "detection": detection,
                "elapsed_seconds": elapsed_seconds,
                "predicted_lat": predicted_lat,
                "predicted_lon": predicted_lon,
                "distance_m": distance,
                "corridor_radius_m": corridor_radius,
            })

    # Select the closest one-to-one vessel-report/detection matches.
    possible_matches.sort(key=lambda item: item["distance_m"])
    used_reports = set()
    used_detections = set()
    matches = []

    for item in possible_matches:
        if item["report_index"] in used_reports:
            continue
        if item["detection_index"] in used_detections:
            continue
        if item["distance_m"] > item["corridor_radius_m"]:
            continue

        used_reports.add(item["report_index"])
        used_detections.add(item["detection_index"])

        matches.append({
            "mmsi": item["vessel"]["mmsi"],
            "detection_id": item["detection"].get(
                "detection_id", str(item["detection_index"])
            ),
            "hours_since_last_ais": item["elapsed_seconds"] / 3600,
            "predicted_position": {
                "lat": item["predicted_lat"],
                "lon": item["predicted_lon"],
            },
            "detection_distance_m": round(item["distance_m"], 1),
            "corridor_radius_m": round(item["corridor_radius_m"], 1),
            "status": "sar_detection_consistent_with_dead_reckoning",
            "interpretation": (
                "Detection falls within the configured projected corridor; "
                "this is a candidate association, not identity confirmation."
            ),
        })

    unmatched = [
        {
            "detection_id": detection.get("detection_id", str(index)),
            "status": "not_matched_to_known_ais_gap_corridor",
            "interpretation": (
                "No configured dead-reckoning corridor matched this detection; "
                "it may be an unreported vessel or detection clutter."
            ),
        }
        for index, detection in enumerate(case["sar_detections"])
        if index not in used_detections
    ]

    return {
        "matches": matches,
        "unmatched_sar_detections": unmatched,
        "score_meaning": (
            "Constant-course dead reckoning with a configured uncertainty "
            "corridor; not proof of a dark vessel or AIS tampering."
        ),
    }


def main():
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: python -m backend.forensics.dead_reckoning "
            "scenarios/dead_reckoning_demo.json"
        )

    path = Path(sys.argv[1])
    case = json.loads(path.read_text(encoding="utf-8-sig"))
    print(json.dumps(assess_gap_detections(case), indent=2))


if __name__ == "__main__":
    main()