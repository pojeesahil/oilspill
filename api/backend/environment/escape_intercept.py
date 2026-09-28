import json
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


def parse_time(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("vessel.time must include a timezone")
    return result.astimezone(timezone.utc)


def get_polygons(geometry):
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates")

    if geometry_type == "Polygon":
        return [coordinates]
    if geometry_type == "MultiPolygon":
        return coordinates

    raise ValueError(
        "jurisdiction_geometry must be a GeoJSON Polygon or MultiPolygon"
    )


def validate_geometry(geometry):
    polygons = get_polygons(geometry)
    if not polygons:
        raise ValueError("jurisdiction_geometry contains no polygons")

    for polygon in polygons:
        if not polygon:
            raise ValueError("Polygon has no outer ring")

        for ring in polygon:
            if len(ring) < 4 or ring[0] != ring[-1]:
                raise ValueError(
                    "Each polygon ring must be closed and have at least 4 points"
                )

            for position in ring:
                if len(position) < 2:
                    raise ValueError(
                        "GeoJSON positions must contain longitude and latitude"
                    )


def point_in_ring(lon, lat, ring):
    inside = False

    for index in range(len(ring) - 1):
        lon1, lat1 = ring[index][:2]
        lon2, lat2 = ring[index + 1][:2]

        crosses_latitude = (lat1 > lat) != (lat2 > lat)
        if crosses_latitude:
            crossing_lon = lon1 + (
                (lat - lat1) * (lon2 - lon1) / (lat2 - lat1)
            )
            if lon < crossing_lon:
                inside = not inside

    return inside


def geometry_contains(geometry, lon, lat):
    for polygon in get_polygons(geometry):
        inside_outer = point_in_ring(lon, lat, polygon[0])
        inside_hole = any(
            point_in_ring(lon, lat, hole)
            for hole in polygon[1:]
        )

        if inside_outer and not inside_hole:
            return True

    return False


def position_after(vessel, hours, earth_radius_m, meters_per_nautical_mile):
    latitude_1 = math.radians(float(vessel["lat"]))
    longitude_1 = math.radians(float(vessel["lon"]))
    bearing = math.radians(float(vessel["course_over_ground_deg"]))

    distance_m = (
        float(vessel["speed_knots"])
        * meters_per_nautical_mile
        * hours
    )
    angular_distance = distance_m / earth_radius_m

    latitude_2 = math.asin(
        math.sin(latitude_1) * math.cos(angular_distance)
        + math.cos(latitude_1)
        * math.sin(angular_distance)
        * math.cos(bearing)
    )
    longitude_2 = longitude_1 + math.atan2(
        math.sin(bearing)
        * math.sin(angular_distance)
        * math.cos(latitude_1),
        math.cos(angular_distance)
        - math.sin(latitude_1) * math.sin(latitude_2),
    )

    return {
        "lat": math.degrees(latitude_2),
        "lon": math.degrees(longitude_2),
    }


def distance_m(a, b, earth_radius_m):
    latitude_1 = math.radians(float(a["lat"]))
    latitude_2 = math.radians(float(b["lat"]))
    latitude_delta = latitude_2 - latitude_1
    longitude_delta = math.radians(float(b["lon"]) - float(a["lon"]))

    haversine = (
        math.sin(latitude_delta / 2) ** 2
        + math.cos(latitude_1)
        * math.cos(latitude_2)
        * math.sin(longitude_delta / 2) ** 2
    )

    return 2 * earth_radius_m * math.asin(
        min(1.0, math.sqrt(haversine))
    )


def find_boundary_exit(vessel, boundary, config):
    earth_radius_m = float(config["earth_radius_m"])
    meters_per_nautical_mile = float(
        config["meters_per_nautical_mile"]
    )
    step_hours = float(config["boundary_step_minutes"]) / 60
    horizon_hours = float(config["max_projection_hours"])
    refinement_iterations = int(config["refinement_iterations"])

    if step_hours <= 0 or horizon_hours <= 0:
        raise ValueError(
            "boundary_step_minutes and max_projection_hours must be positive"
        )
    if refinement_iterations <= 0:
        raise ValueError("refinement_iterations must be positive")

    start = {
        "lat": float(vessel["lat"]),
        "lon": float(vessel["lon"]),
    }

    if not geometry_contains(boundary, start["lon"], start["lat"]):
        return None, "vessel_not_inside_configured_boundary"

    previous_time = 0.0
    current_time = min(step_hours, horizon_hours)

    while True:
        position = position_after(
            vessel,
            current_time,
            earth_radius_m,
            meters_per_nautical_mile,
        )

        if not geometry_contains(
            boundary, position["lon"], position["lat"]
        ):
            low = previous_time
            high = current_time

            for _ in range(refinement_iterations):
                middle = (low + high) / 2
                middle_position = position_after(
                    vessel,
                    middle,
                    earth_radius_m,
                    meters_per_nautical_mile,
                )

                if geometry_contains(
                    boundary,
                    middle_position["lon"],
                    middle_position["lat"],
                ):
                    low = middle
                else:
                    high = middle

            exit_position = position_after(
                vessel,
                high,
                earth_radius_m,
                meters_per_nautical_mile,
            )

            return {
                "eta_hours": high,
                "time": (
                    parse_time(vessel["time"])
                    + timedelta(hours=high)
                ).isoformat(),
                "position": exit_position,
            }, "projected_exit_found"

        if current_time >= horizon_hours:
            break

        previous_time = current_time
        current_time = min(
            current_time + step_hours,
            horizon_hours,
        )

    return None, "inside_through_projection_horizon"


def find_interception(vessel, patrol_bases, exit_result, config):
    if exit_result is None:
        return None

    earth_radius_m = float(config["earth_radius_m"])
    meters_per_nautical_mile = float(
        config["meters_per_nautical_mile"]
    )
    step_hours = float(config["intercept_step_minutes"]) / 60
    safety_margin_hours = float(config["safety_margin_hours"])
    exit_eta_hours = float(exit_result["eta_hours"])

    if step_hours <= 0:
        raise ValueError("intercept_step_minutes must be positive")

    best = None
    target_time = step_hours

    while target_time < exit_eta_hours - safety_margin_hours:
        target = position_after(
            vessel,
            target_time,
            earth_radius_m,
            meters_per_nautical_mile,
        )

        for base in patrol_bases:
            patrol_speed_knots = float(base["patrol_speed_knots"])
            mobilization_delay_hours = float(
                base["mobilization_delay_hours"]
            )

            if patrol_speed_knots <= 0:
                raise ValueError("patrol_speed_knots must be positive")

            distance = distance_m(
                {"lat": base["lat"], "lon": base["lon"]},
                target,
                earth_radius_m,
            )
            patrol_travel_hours = (
                distance
                / (patrol_speed_knots * meters_per_nautical_mile)
            )
            patrol_eta_hours = (
                patrol_travel_hours + mobilization_delay_hours
            )
            time_margin_hours = target_time - patrol_eta_hours

            if time_margin_hours >= safety_margin_hours:
                candidate = {
                    "base": base["name"],
                    "position": target,
                    "vessel_eta_hours": target_time,
                    "patrol_eta_hours": patrol_eta_hours,
                    "time_margin_hours": time_margin_hours,
                }

                if best is None or (
                    candidate["vessel_eta_hours"],
                    candidate["patrol_eta_hours"],
                ) < (
                    best["vessel_eta_hours"],
                    best["patrol_eta_hours"],
                ):
                    best = candidate

        target_time += step_hours

    if best:
        best["time"] = (
            parse_time(vessel["time"])
            + timedelta(hours=best["vessel_eta_hours"])
        ).isoformat()

    return best


def analyze(scenario):
    config = scenario["config"]
    boundary = scenario["jurisdiction_geometry"]
    validate_geometry(boundary)

    exit_result, exit_status = find_boundary_exit(
        scenario["vessel"],
        boundary,
        config,
    )
    interception = find_interception(
        scenario["vessel"],
        scenario["patrol_bases"],
        exit_result,
        config,
    )

    return {
        "scenario_label": scenario.get("scenario_label"),
        "vessel_id": scenario["vessel"]["id"],
        "jurisdiction_status": exit_status,
        "projected_boundary_exit": exit_result,
        "interception_estimate": interception,
        "interpretation": (
            "Estimate assumes constant course and speed and uses the supplied "
            "boundary and patrol-base data. It is not a live operational "
            "tracking or dispatch recommendation."
        ),
    }


def main():
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: python -m backend.environment.escape_intercept "
            "SCENARIO.json"
        )

    scenario = json.loads(
        Path(sys.argv[1]).read_text(encoding="utf-8-sig")
    )
    print(json.dumps(analyze(scenario), indent=2))


if __name__ == "__main__":
    main()