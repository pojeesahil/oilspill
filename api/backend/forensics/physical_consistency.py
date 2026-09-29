import math


ORIENTATION_CONFIG_KEY = "orientation_minimum_anisotropy"


def _to_local(lon, lat, origin, earth_radius_m):
    latitude_0 = math.radians(origin["lat"])
    return (
        earth_radius_m
        * math.cos(latitude_0)
        * math.radians(lon - origin["lon"]),
        earth_radius_m * math.radians(lat - origin["lat"]),
    )


def _ring_area(ring):
    return abs(
        sum(
            ring[i][0] * ring[i + 1][1]
            - ring[i + 1][0] * ring[i][1]
            for i in range(len(ring) - 1)
        )
        / 2.0
    )


def _point_in_ring(point, ring):
    x, y = point
    inside = False

    for index in range(len(ring) - 1):
        x1, y1 = ring[index]
        x2, y2 = ring[index + 1]

        if (y1 > y) != (y2 > y):
            crossing_x = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < crossing_x:
                inside = not inside

    return inside


def _convex_hull(points):
    points = sorted(set(points))
    if len(points) <= 1:
        return points

    def cross(origin, point_a, point_b):
        return (
            (point_a[0] - origin[0]) * (point_b[1] - origin[1])
            - (point_a[1] - origin[1]) * (point_b[0] - origin[0])
        )

    lower = []
    for point in points:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0:
            lower.pop()
        lower.append(point)

    upper = []
    for point in reversed(points):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0:
            upper.pop()
        upper.append(point)

    return lower[:-1] + upper[:-1]


def _orientation(points, minimum_anisotropy):
    if len(points) < 2:
        return None

    mean_x = sum(point[0] for point in points) / len(points)
    mean_y = sum(point[1] for point in points) / len(points)

    variance_x = sum(
        (x - mean_x) ** 2 for x, _ in points
    ) / len(points)
    variance_y = sum(
        (y - mean_y) ** 2 for _, y in points
    ) / len(points)
    covariance_xy = sum(
        (x - mean_x) * (y - mean_y) for x, y in points
    ) / len(points)

    discriminant = math.sqrt(
        (variance_x - variance_y) ** 2
        + 4 * covariance_xy ** 2
    )
    major_variance = (variance_x + variance_y + discriminant) / 2.0
    minor_variance = (variance_x + variance_y - discriminant) / 2.0

    if major_variance <= 0:
        return None

    anisotropy = (major_variance - minor_variance) / major_variance
    if anisotropy < minimum_anisotropy:
        return None

    angle = 0.5 * math.degrees(
        math.atan2(
            2 * covariance_xy,
            variance_x - variance_y,
        )
    )
    return angle % 180


def _polygon_rings(footprint_geojson, origin, earth_radius_m):
    if footprint_geojson.get("type") != "Polygon":
        raise ValueError(
            "observation.footprint_geojson must be a GeoJSON Polygon"
        )

    coordinates = footprint_geojson.get("coordinates", [])
    if not coordinates:
        raise ValueError("Observed footprint has no polygon rings")

    rings = []
    for ring in coordinates:
        if len(ring) < 4 or ring[0] != ring[-1]:
            raise ValueError(
                "Each footprint ring must be closed and have at least 4 points"
            )

        rings.append([
            _to_local(
                float(position[0]),
                float(position[1]),
                origin,
                earth_radius_m,
            )
            for position in ring
        ])

    return rings


def _metric_label(name):
    labels = {
        "centroid_fraction": "centroid consistency",
        "polygon_support_fraction": "polygon support",
        "area_similarity": "area similarity",
        "orientation_similarity": "orientation similarity",
    }
    return labels.get(name, name.replace("_", " "))


def score_ensemble(
    endpoints,
    footprint_geojson,
    centroid,
    earth_radius_m,
    match_radius_m,
    weights,
):
    if not endpoints:
        raise ValueError("Cannot score an empty endpoint ensemble")

    if ORIENTATION_CONFIG_KEY not in weights:
        raise ValueError(
            f"Add '{ORIENTATION_CONFIG_KEY}' to analysis.vector_weights"
        )

    minimum_anisotropy = float(weights[ORIENTATION_CONFIG_KEY])
    if not 0 <= minimum_anisotropy < 1:
        raise ValueError(f"{ORIENTATION_CONFIG_KEY} must be in [0, 1)")

    metric_weights = {
        name: value
        for name, value in weights.items()
        if name != ORIENTATION_CONFIG_KEY
    }

    observed_rings = _polygon_rings(
        footprint_geojson,
        centroid,
        earth_radius_m,
    )

    observed_area = (
        _ring_area(observed_rings[0])
        - sum(_ring_area(hole) for hole in observed_rings[1:])
    )
    if observed_area <= 0:
        raise ValueError("Observed footprint area must be positive")

    local_endpoints = [
        _to_local(
            float(endpoint["lon"]),
            float(endpoint["lat"]),
            centroid,
            earth_radius_m,
        )
        for endpoint in endpoints
    ]

    envelope = _convex_hull(local_endpoints)
    envelope_area = (
        _ring_area(envelope + [envelope[0]])
        if len(envelope) >= 3
        else 0.0
    )

    inside_observed = 0
    for point in local_endpoints:
        inside_outer = _point_in_ring(point, observed_rings[0])
        inside_hole = any(
            _point_in_ring(point, hole)
            for hole in observed_rings[1:]
        )
        if inside_outer and not inside_hole:
            inside_observed += 1

    centroid_matches = sum(
        math.hypot(x, y) <= match_radius_m
        for x, y in local_endpoints
    )

    polygon_support_fraction = inside_observed / len(local_endpoints)
    centroid_fraction = centroid_matches / len(local_endpoints)

    area_similarity = (
        min(envelope_area, observed_area) / max(envelope_area, observed_area)
        if envelope_area > 0
        else 0.0
    )

    envelope_orientation = _orientation(envelope, minimum_anisotropy)
    observed_orientation = _orientation(
        observed_rings[0][:-1],
        minimum_anisotropy,
    )

    orientation_similarity = None
    if envelope_orientation is not None and observed_orientation is not None:
        difference = abs(envelope_orientation - observed_orientation) % 180
        difference = min(difference, 180 - difference)
        orientation_similarity = 1.0 - difference / 90.0

    components = {
        "centroid_fraction": centroid_fraction,
        "polygon_support_fraction": polygon_support_fraction,
        "area_similarity": area_similarity,
        "orientation_similarity": orientation_similarity,
    }

    known_metrics = set(components)
    unknown_metrics = set(metric_weights) - known_metrics
    if unknown_metrics:
        raise ValueError(
            "Unknown vector weight names: "
            + ", ".join(sorted(unknown_metrics))
        )

    weighted_sum = 0.0
    weight_sum = 0.0
    score_components_used = []
    score_components_excluded = {}

    for name, raw_weight in metric_weights.items():
        weight = float(raw_weight)
        if weight < 0:
            raise ValueError("Vector weights must be non-negative")

        value = components[name]

        if weight == 0:
            score_components_excluded[name] = "Configured weight is zero."
        elif value is None:
            score_components_excluded[name] = (
                "Metric is indeterminate for this geometry."
            )
        else:
            weighted_sum += weight * value
            weight_sum += weight
            score_components_used.append(name)

    if weight_sum <= 0:
        raise ValueError(
            "At least one usable vector weight must be positive"
        )

    if observed_orientation is None:
        orientation_status = "observed_footprint_orientation_indeterminate"
    elif envelope_orientation is None:
        orientation_status = "endpoint_envelope_orientation_indeterminate"
    else:
        orientation_status = "orientation_compared"

    if orientation_similarity is None:
        orientation_note = (
            "Orientation was indeterminate and excluded from the composite score."
        )
    elif "orientation_similarity" not in score_components_used:
        orientation_note = (
            "Orientation similarity was calculated but excluded from the "
            "composite score because its configured weight is zero."
        )
    else:
        orientation_note = (
            "Orientation similarity was compared and included in the "
            "composite score."
        )

    used_labels = [_metric_label(name) for name in score_components_used]
    used_summary = ", ".join(used_labels)

    return {
        "endpoint_count": len(endpoints),
        "endpoint_envelope_area_m2": round(envelope_area, 2),
        "observed_footprint_area_m2": round(observed_area, 2),
        "endpoint_envelope_orientation_deg": (
            round(envelope_orientation, 2)
            if envelope_orientation is not None
            else None
        ),
        "observed_footprint_orientation_deg": (
            round(observed_orientation, 2)
            if observed_orientation is not None
            else None
        ),
        "orientation_status": orientation_status,
        "centroid_fraction": round(centroid_fraction, 4),
        "polygon_support_fraction": round(polygon_support_fraction, 4),
        "area_similarity": round(area_similarity, 4),
        "orientation_similarity": (
            round(orientation_similarity, 4)
            if orientation_similarity is not None
            else None
        ),
        "score_components_used": score_components_used,
        "score_components_excluded": score_components_excluded,
        "physical_consistency_score": round(
            weighted_sum / weight_sum,
            4,
        ),
        "interpretation": (
            f"Composite score uses {used_summary}. "
            f"{orientation_note} "
            "This endpoint-envelope geometry proxy is not a resolved "
            "slick-shape model."
        ),
    }