import json
import math
import sys
from pathlib import Path

from backend.ocean.drift import parse_time


def _distance_m(lat1, lon1, lat2, lon2, earth_radius_m):
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lam = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2) ** 2
    )
    return 2 * earth_radius_m * math.asin(math.sqrt(min(1.0, a)))


def _inside_ring(lon, lat, ring):
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


def _inside_footprint(lon, lat, geometry):
    if geometry["type"] == "Polygon":
        polygons = [geometry["coordinates"]]
    elif geometry["type"] == "MultiPolygon":
        polygons = geometry["coordinates"]
    else:
        raise ValueError("SAR footprint must be Polygon or MultiPolygon")

    for polygon in polygons:
        if polygon and _inside_ring(lon, lat, polygon[0]):
            in_hole = any(_inside_ring(lon, lat, hole) for hole in polygon[1:])
            if not in_hole:
                return True

    return False


def verify_sar_ais(case):
    limits = case["limits"]
    sar_scene = case["sar_scene"]
    sar_time = parse_time(sar_scene["acquisition_time"])
    geometry = sar_scene["footprint"]

    max_distance = limits["max_match_distance_m"]
    max_time_delta = limits["max_time_delta_seconds"]
    earth_radius = limits["earth_radius_m"]

    if max_distance <= 0 or max_time_delta < 0 or earth_radius <= 0:
        raise ValueError("Invalid SAR/AIS matching limits")

    detections = case["sar_detections"]
    ais_positions = case["ais_positions"]
    possible_matches = []

    for detection_index, detection in enumerate(detections):
        detection_time = parse_time(detection.get("time", sar_scene["acquisition_time"]))

        for ais_index, report in enumerate(ais_positions):
            ais_time = parse_time(report["time"])
            time_delta = abs((detection_time - ais_time).total_seconds())

            if time_delta > max_time_delta:
                continue

            distance = _distance_m(
                detection["lat"],
                detection["lon"],
                report["lat"],
                report["lon"],
                earth_radius,
            )
            if distance <= max_distance:
                possible_matches.append(
                    (distance, time_delta, detection_index, ais_index)
                )

    # Greedily take the closest one-to-one position/time matches.
    possible_matches.sort()
    matched_detections = set()
    matched_ais = set()
    matches = []

    for distance, time_delta, detection_index, ais_index in possible_matches:
        if detection_index in matched_detections or ais_index in matched_ais:
            continue

        matched_detections.add(detection_index)
        matched_ais.add(ais_index)
        matches.append({
            "detection_id": detections[detection_index].get(
                "detection_id", str(detection_index)
            ),
            "mmsi": ais_positions[ais_index]["mmsi"],
            "distance_m": round(distance, 1),
            "time_delta_seconds": round(time_delta, 1),
            "status": "position_time_match",
            "interpretation": (
                "SAR detection and AIS report align spatially and in time; "
                "this does not authenticate vessel identity."
            ),
        })

    unmatched_sar = [
        {
            "detection_id": detection.get("detection_id", str(index)),
            "lat": detection["lat"],
            "lon": detection["lon"],
            "status": "unmatched_sar_detection",
            "interpretation": (
                "Possible unreported vessel or detection clutter; requires review."
            ),
        }
        for index, detection in enumerate(detections)
        if index not in matched_detections
    ]

    unmatched_ais_in_scene = []
    for index, report in enumerate(ais_positions):
        if index in matched_ais:
            continue

        report_time = parse_time(report["time"])
        delta = abs((sar_time - report_time).total_seconds())

        if (
            delta <= max_time_delta
            and _inside_footprint(report["lon"], report["lat"], geometry)
        ):
            unmatched_ais_in_scene.append({
                "mmsi": report["mmsi"],
                "time": report["time"],
                "status": "ais_position_without_sar_match",
                "interpretation": (
                    "No corresponding SAR detection in this comparison; "
                    "not proof of spoofing or a false AIS report."
                ),
            })

    return {
        "sar_acquisition_time": sar_scene["acquisition_time"],
        "matches": matches,
        "unmatched_sar_detections": unmatched_sar,
        "ais_positions_without_sar_match_inside_scene": unmatched_ais_in_scene,
        "score_meaning": (
            "Spatial-temporal cross-check only. Sensor resolution, sea state, "
            "AIS timing, and scene coverage can produce unmatched reports."
        ),
    }


def main():
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: python -m backend.forensics.ais_trust "
            "scenarios/ais_trust_demo.json"
        )

    path = Path(sys.argv[1])
    case = json.loads(path.read_text(encoding="utf-8-sig"))
    print(json.dumps(verify_sar_ais(case), indent=2))


if __name__ == "__main__":
    main()