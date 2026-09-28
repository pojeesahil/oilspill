"""Multi-ship analytics service integrating physics engines from backend/.

Provides realistic multi-vessel tracking, forward drift forecasting,
backward hindcast backtracking, counterfactual attribution, and ecological impact.
"""

from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path

from backend.ocean.drift import DriftConfig, DriftForcing, monte_carlo_hindcast, simulate_drift
from backend.vessels.surveillance import analyze_track
from backend.forensics.counterfactual import evaluate_counterfactuals
from backend.environment.impact import forecast_hypothetical_impact
from backend.environment.opportunity import calculate_spill_opportunity
from backend.environment.uncertainty import calculate_data_uncertainty
from backend.environment.pre_spill import evaluate_pre_spill_candidate, rank_surveillance_candidates

BASE_SETTINGS = {
    "earth_radius_m": 6371008.8,
    "meters_per_second_per_knot": 0.514444,
    "risk_decay_per_hour": 0.12,
    "evidence_gain": 0.5,
    "initial_risk": 0.08,
    "reason_display_threshold": 0.4,
    "weights": {
        "speed_deviation": 0.25,
        "loitering": 0.20,
        "ais_gap": 0.20,
        "kinematic": 0.15,
        "route_deviation": 0.10,
        "course_change": 0.10,
    },
    "speed_z_score": {"start": 1.0, "full": 3.0},
    "loitering": {
        "speed_limit_knots": 3.0,
        "duration_start_seconds": 600,
        "duration_full_seconds": 1800,
        "max_interval_seconds": 900,
    },
    "ais_gap": {
        "duration_start_seconds": 900,
        "duration_full_seconds": 3600,
    },
    "kinematic": {"speed_ratio_start": 1.0, "speed_ratio_full": 1.5},
    "route_deviation": {"degrees_start": 25, "degrees_full": 90},
    "course_change": {
        "degrees_per_minute_start": 1.0,
        "degrees_per_minute_full": 8.0,
    },
}

CONTEXTUAL_BASELINES = {
    "tanker": {
        "open_water": {
            "speed_mean_knots": 11.5,
            "speed_std_knots": 2.5,
            "max_speed_knots": 18.0,
        }
    },
    "cargo": {
        "open_water": {
            "speed_mean_knots": 12.0,
            "speed_std_knots": 2.0,
            "max_speed_knots": 19.0,
        }
    },
    "container": {
        "open_water": {
            "speed_mean_knots": 15.0,
            "speed_std_knots": 2.5,
            "max_speed_knots": 23.0,
        }
    },
}

DEFAULT_FORCING = DriftForcing(
    current_east_mps=0.15,
    current_north_mps=0.05,
    wind_east_mps=2.0,
    wind_north_mps=1.0,
    current_uncertainty_mps=0.08,
    wind_uncertainty_mps=0.5,
)

DEFAULT_PHYSICS = DriftConfig(
    earth_radius_m=6371008.8,
    step_seconds=600,
    windage=0.03,
    diffusion_m2ps=2.0,
    longitude_cosine_floor=0.001,
)

ECOSYSTEM_ZONES = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {
                "name": "Prongs Reef Sanctuary",
                "consequence_weight": 1.0,
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [72.70, 18.94],
                        [72.78, 18.94],
                        [72.78, 19.08],
                        [72.70, 19.08],
                        [72.70, 18.94],
                    ]
                ],
            },
        },
        {
            "type": "Feature",
            "properties": {
                "name": "Malabar Marine Zone",
                "consequence_weight": 0.85,
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [72.72, 18.78],
                        [72.82, 18.78],
                        [72.82, 18.92],
                        [72.72, 18.92],
                        [72.72, 18.78],
                    ]
                ],
            },
        },
        {
            "type": "Feature",
            "properties": {
                "name": "Mahim Estuary Biosphere",
                "consequence_weight": 0.90,
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [72.76, 19.12],
                        [72.86, 19.12],
                        [72.86, 19.26],
                        [72.76, 19.26],
                        [72.76, 19.12],
                    ]
                ],
            },
        },
    ],
}

# The 3 canonical ships from the mission briefing & Figma command view
SHIPS_SPEC = [
    {
        "mmsi": "IND-7319",
        "name": "PRAGATI",
        "code": "IND-7319",
        "type": "tanker",
        "operating_context": "open_water",
        "state": "AIS DARK",
        "className": "target-pragati",
        "map_coords": {"left_pct": 45, "top_pct": 52},
        "reported_bearing": "247°",
        "reported_speed": "02.1 KN",
        "opportunity_signals": {
            "vessel_spill_capability": 1.0,
            "operational_context": 0.85,
            "sensitive_area_downstream": 0.88,
            "release_conditions": 0.75,
        },
        "opportunity_weights": {
            "vessel_spill_capability": 0.35,
            "operational_context": 0.20,
            "sensitive_area_downstream": 0.25,
            "release_conditions": 0.20,
        },
        "uncertainty_signals": {
            "ais_freshness_uncertainty": 0.65,
            "identity_uncertainty": 0.20,
            "environmental_data_uncertainty": 0.50,
        },
        "uncertainty_weights": {
            "ais_freshness_uncertainty": 0.40,
            "identity_uncertainty": 0.20,
            "environmental_data_uncertainty": 0.40,
        },
        "ais_points": [
            {
                "time": "2026-09-26T06:00:00Z",
                "lat": 18.850,
                "lon": 72.550,
                "sog_knots": 12.0,
                "cog_deg": 45.0,
                "expected_route_bearing_deg": 45.0,
            },
            {
                "time": "2026-09-26T06:30:00Z",
                "lat": 18.870,
                "lon": 72.570,
                "sog_knots": 3.0,
                "cog_deg": 80.0,
                "expected_route_bearing_deg": 45.0,
            },
            {
                "time": "2026-09-26T07:00:00Z",
                "lat": 18.870,
                "lon": 72.570,
                "sog_knots": 2.0,
                "cog_deg": 95.0,
                "expected_route_bearing_deg": 45.0,
            },
            {
                "time": "2026-09-26T07:50:00Z",
                "lat": 18.871,
                "lon": 72.571,
                "sog_knots": 2.0,
                "cog_deg": 95.0,
                "expected_route_bearing_deg": 45.0,
            },
            {
                "time": "2026-09-26T08:05:00Z",
                "lat": 19.000,
                "lon": 72.630,
                "sog_knots": 20.0,
                "cog_deg": 45.0,
                "expected_route_bearing_deg": 45.0,
            },
        ],
    },
    {
        "mmsi": "PAN-4802",
        "name": "OCEAN CREST",
        "code": "PAN-4802",
        "type": "cargo",
        "operating_context": "open_water",
        "state": "LOITERING",
        "className": "target-crest",
        "map_coords": {"left_pct": 27, "top_pct": 67},
        "reported_bearing": "118°",
        "reported_speed": "03.4 KN",
        "opportunity_signals": {
            "vessel_spill_capability": 0.70,
            "operational_context": 0.65,
            "sensitive_area_downstream": 0.60,
            "release_conditions": 0.55,
        },
        "opportunity_weights": {
            "vessel_spill_capability": 0.35,
            "operational_context": 0.20,
            "sensitive_area_downstream": 0.25,
            "release_conditions": 0.20,
        },
        "uncertainty_signals": {
            "ais_freshness_uncertainty": 0.25,
            "identity_uncertainty": 0.15,
            "environmental_data_uncertainty": 0.45,
        },
        "uncertainty_weights": {
            "ais_freshness_uncertainty": 0.30,
            "identity_uncertainty": 0.20,
            "environmental_data_uncertainty": 0.50,
        },
        "ais_points": [
            {
                "time": "2026-09-26T05:30:00Z",
                "lat": 18.680,
                "lon": 72.450,
                "sog_knots": 11.5,
                "cog_deg": 115.0,
                "expected_route_bearing_deg": 115.0,
            },
            {
                "time": "2026-09-26T06:15:00Z",
                "lat": 18.705,
                "lon": 72.475,
                "sog_knots": 3.8,
                "cog_deg": 118.0,
                "expected_route_bearing_deg": 115.0,
            },
            {
                "time": "2026-09-26T07:00:00Z",
                "lat": 18.712,
                "lon": 72.482,
                "sog_knots": 2.5,
                "cog_deg": 120.0,
                "expected_route_bearing_deg": 115.0,
            },
            {
                "time": "2026-09-26T07:45:00Z",
                "lat": 18.716,
                "lon": 72.486,
                "sog_knots": 2.2,
                "cog_deg": 122.0,
                "expected_route_bearing_deg": 115.0,
            },
            {
                "time": "2026-09-26T08:30:00Z",
                "lat": 18.725,
                "lon": 72.495,
                "sog_knots": 3.4,
                "cog_deg": 118.0,
                "expected_route_bearing_deg": 115.0,
            },
        ],
    },
    {
        "mmsi": "LBR-2108",
        "name": "MERIDIAN VIII",
        "code": "LBR-2108",
        "type": "container",
        "operating_context": "open_water",
        "state": "ROUTE DEV.",
        "className": "target-meridian",
        "map_coords": {"left_pct": 67, "top_pct": 31},
        "reported_bearing": "032°",
        "reported_speed": "11.8 KN",
        "opportunity_signals": {
            "vessel_spill_capability": 0.50,
            "operational_context": 0.50,
            "sensitive_area_downstream": 0.45,
            "release_conditions": 0.50,
        },
        "opportunity_weights": {
            "vessel_spill_capability": 0.35,
            "operational_context": 0.20,
            "sensitive_area_downstream": 0.25,
            "release_conditions": 0.20,
        },
        "uncertainty_signals": {
            "ais_freshness_uncertainty": 0.15,
            "identity_uncertainty": 0.10,
            "environmental_data_uncertainty": 0.40,
        },
        "uncertainty_weights": {
            "ais_freshness_uncertainty": 0.30,
            "identity_uncertainty": 0.20,
            "environmental_data_uncertainty": 0.50,
        },
        "ais_points": [
            {
                "time": "2026-09-26T06:00:00Z",
                "lat": 19.200,
                "lon": 72.380,
                "sog_knots": 14.8,
                "cog_deg": 32.0,
                "expected_route_bearing_deg": 85.0,
            },
            {
                "time": "2026-09-26T06:45:00Z",
                "lat": 19.255,
                "lon": 72.425,
                "sog_knots": 13.9,
                "cog_deg": 35.0,
                "expected_route_bearing_deg": 85.0,
            },
            {
                "time": "2026-09-26T07:30:00Z",
                "lat": 19.310,
                "lon": 72.470,
                "sog_knots": 12.8,
                "cog_deg": 30.0,
                "expected_route_bearing_deg": 85.0,
            },
            {
                "time": "2026-09-26T08:15:00Z",
                "lat": 19.360,
                "lon": 72.510,
                "sog_knots": 11.8,
                "cog_deg": 32.0,
                "expected_route_bearing_deg": 85.0,
            },
        ],
    },
]

OBSERVED_SLICK = {
    "case_id": "MUM-04",
    "label": "MUM-04 · Western Offshore",
    "detected_time": "18 JUN · 22:48 IST",
    "satellite_scene": "S1A-IW-GRD",
    "slick_area_km2": 12.8,
    "est_age": "03H 36M",
    "orientation": "NE 042°",
    "time": "2026-09-26T12:00:00Z",
    "centroid": {"lat": 18.882, "lon": 72.601},
}


def build_ship_case(spec):
    """Build case dictionary for analyze_track."""
    return {
        "vessel": {
            "mmsi": spec["mmsi"],
            "type": spec["type"],
            "operating_context": spec["operating_context"],
        },
        "contextual_baselines": CONTEXTUAL_BASELINES,
        "ais_points": spec["ais_points"],
        "settings": BASE_SETTINGS,
    }


def compute_multi_ship_data():
    """Run physics, behavior, and attribution engines for all 3 ships."""
    ships_output = []
    attribution_candidates = []

    # First pass: prepare candidate tracks for counterfactual attribution
    for spec in SHIPS_SPEC:
        attribution_candidates.append({
            "mmsi": spec["mmsi"],
            "track": [
                {"time": pt["time"], "lat": pt["lat"], "lon": pt["lon"]}
                for pt in spec["ais_points"]
            ],
        })

    # Run overall counterfactual attribution against observed slick
    attribution_scenario = {
        "observation": {
            "time": OBSERVED_SLICK["time"],
            "centroid": OBSERVED_SLICK["centroid"],
        },
        "analysis": {
            "min_hours_before": 3,
            "max_hours_before": 8,
            "run_count": 80,
            "match_radius_m": 6000,
            "minimum_consistency_fraction": 0.40,
            "random_seed": 143,
        },
        "drift_config": {
            "earth_radius_m": DEFAULT_PHYSICS.earth_radius_m,
            "step_seconds": DEFAULT_PHYSICS.step_seconds,
            "windage": DEFAULT_PHYSICS.windage,
            "diffusion_m2ps": DEFAULT_PHYSICS.diffusion_m2ps,
            "longitude_cosine_floor": DEFAULT_PHYSICS.longitude_cosine_floor,
        },
        "forcing": {
            "current_east_mps": DEFAULT_FORCING.current_east_mps,
            "current_north_mps": DEFAULT_FORCING.current_north_mps,
            "wind_east_mps": DEFAULT_FORCING.wind_east_mps,
            "wind_north_mps": DEFAULT_FORCING.wind_north_mps,
            "current_uncertainty_mps": DEFAULT_FORCING.current_uncertainty_mps,
            "wind_uncertainty_mps": DEFAULT_FORCING.wind_uncertainty_mps,
        },
        "candidates": attribution_candidates,
    }

    attribution_results = evaluate_counterfactuals(attribution_scenario)
    attr_by_mmsi = {cand["mmsi"]: cand for cand in attribution_results["candidates"]}

    # Second pass: compute individual ship telemetry, drift forecast & backtrack
    for idx, spec in enumerate(SHIPS_SPEC):
        mmsi = spec["mmsi"]
        case = build_ship_case(spec)
        vessel_analysis = analyze_track(case)

        last_ais = spec["ais_points"][-1]
        lat = last_ais["lat"]
        lon = last_ais["lon"]
        time_str = last_ais["time"]

        # 1. Forward Drift Forecast (predict future path 24 hours ahead)
        seed_offset = 100 + idx * 47
        forward_track = simulate_drift(
            lat=lat,
            lon=lon,
            start_time=time_str,
            duration_hours=24.0,
            forcing=DEFAULT_FORCING,
            config=DEFAULT_PHYSICS,
            direction=1,
            seed=seed_offset,
        )

        # 2. Backward Backtrack (deterministic reverse drift trajectory)
        backtrack_track = simulate_drift(
            lat=lat,
            lon=lon,
            start_time=time_str,
            duration_hours=8.0,
            forcing=DEFAULT_FORCING,
            config=DEFAULT_PHYSICS,
            direction=-1,
            seed=seed_offset + 1,
        )

        # 3. Monte Carlo Backtrack (Probabilistic Origin Hindcast)
        hindcast = monte_carlo_hindcast(
            observed_lat=lat,
            observed_lon=lon,
            observed_time=time_str,
            min_hours_before=3.0,
            max_hours_before=8.0,
            run_count=50,
            forcing=DEFAULT_FORCING,
            config=DEFAULT_PHYSICS,
            lower_quantile=0.05,
            upper_quantile=0.95,
            seed=seed_offset + 2,
        )

        # 4. Ecological Impact Forecast
        impact_case = {
            "release": {"lat": lat, "lon": lon},
            "forecast": {
                "ensemble_runs": 100,
                "random_seed": 143 + idx * 23,
                "duration_hours": 24,
                "step_minutes": 30,
                "current_east_mps": DEFAULT_FORCING.current_east_mps,
                "current_north_mps": DEFAULT_FORCING.current_north_mps,
                "current_sd_mps": DEFAULT_FORCING.current_uncertainty_mps,
                "wind_east_mps": DEFAULT_FORCING.wind_east_mps,
                "wind_north_mps": DEFAULT_FORCING.wind_north_mps,
                "wind_sd_mps": DEFAULT_FORCING.wind_uncertainty_mps,
                "windage_fraction": DEFAULT_PHYSICS.windage,
                "diffusion_m2_s": DEFAULT_PHYSICS.diffusion_m2ps * 10,
            },
            "ecosystem_zones": ECOSYSTEM_ZONES,
        }
        impact_forecast = forecast_hypothetical_impact(impact_case)

        # 5. Surveillance Prioritization
        opp = calculate_spill_opportunity(
            spec["opportunity_signals"],
            spec["opportunity_weights"],
        )
        unc = calculate_data_uncertainty(
            spec["uncertainty_signals"],
            spec["uncertainty_weights"],
        )

        behavior_score = vessel_analysis["behavior_score"]
        spill_opp = opp["spill_opportunity"]
        data_unc = unc["data_uncertainty"]
        impact_idx = impact_forecast["impact_index"]
        incident_proxy = behavior_score * spill_opp
        priority_index = incident_proxy * impact_idx * data_unc

        surveillance_item = {
            "mmsi": mmsi,
            "behavior_index": round(behavior_score, 4),
            "spill_opportunity": round(spill_opp, 4),
            "potential_impact_index": round(impact_idx, 4),
            "data_uncertainty": round(data_unc, 4),
            "incident_proxy": round(incident_proxy, 4),
            "priority_index": round(priority_index, 4),
            "impact_forecast": impact_forecast,
            "opportunity_breakdown": opp,
            "uncertainty_breakdown": unc,
        }

        ship_obj = {
            "mmsi": mmsi,
            "name": spec["name"],
            "code": spec["code"],
            "vessel_type": spec["type"],
            "operating_context": spec["operating_context"],
            "state": spec["state"],
            "className": spec["className"],
            "map_coords": spec["map_coords"],
            "bearing": spec["reported_bearing"],
            "speed": spec["reported_speed"],
            "current_position": {"lat": lat, "lon": lon},
            "risk": round(behavior_score, 2),
            "vessel_analysis": vessel_analysis,
            "drift_forecast": {
                "forward_track": forward_track,
                "duration_hours": 24.0,
                "endpoint": forward_track[-1],
            },
            "drift_backtrack": {
                "backtrack_track": backtrack_track,
                "duration_hours": 8.0,
                "hindcast": hindcast,
            },
            "attribution": attr_by_mmsi.get(
                mmsi,
                {
                    "mmsi": mmsi,
                    "physical_consistency_fraction": 0.0,
                    "compatible_simulations": 0,
                    "total_simulations": 0,
                    "release_hypotheses": [],
                    "sample_trajectory": [],
                },
            ),
            "impact": impact_forecast,
            "surveillance": surveillance_item,
        }
        ships_output.append(ship_obj)

    # Rank surveillance queue
    ranked_queue = sorted(
        [s["surveillance"] for s in ships_output],
        key=lambda x: x["priority_index"],
        reverse=True,
    )

    primary_ship = ships_output[0]

    return {
        "active_case": OBSERVED_SLICK,
        "ships": ships_output,
        "selected_mmsi": primary_ship["mmsi"],
        "overall_attribution": attribution_results,
        # Backward compatibility with existing frontend types
        "vessel_analysis": primary_ship["vessel_analysis"],
        "drift_analysis": {
            "forward_track": primary_ship["drift_forecast"]["forward_track"],
            "hindcast_origins": primary_ship["drift_backtrack"]["hindcast"],
        },
        "attribution": attribution_results,
        "surveillance_queue": ranked_queue,
    }
