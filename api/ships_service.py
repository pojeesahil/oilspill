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

# Commit 3, 4, 5, 6, 7, 8 modules
from backend.forensics.dead_reckoning import assess_gap_detections
from backend.ocean.forecast_update import update_forecast
from backend.environment.response import build_response_queue
from backend.ocean.observation_planner import rank_observation_windows
from backend.vessels.integrity import inspect_ais_integrity
from backend.vessels.temporal_risk import calculate_temporal_risk
from backend.environment.dynamic_queue import build_dynamic_queue
from backend.forensics.timeline import build_investigation_timeline
from backend.forensics.merge_integrity_timeline import merge_integrity_flags
from backend.forensics.ais_trust import verify_sar_ais
from backend.forensics.dossier import make_dossier
from backend.vessels.contextual_behavior import score_scenario as score_contextual_behavior
from backend.environment.contextual_queue import add_contextual_events
from backend.environment.escape_intercept import analyze as analyze_escape_intercept
from backend.forensics.merge_surveillance_timeline import merge_surveillance_timeline

CURRENT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = CURRENT_DIR.parent
SCENARIOS_DIR = WORKSPACE_ROOT / "scenarios"
OUTPUTS_DIR = WORKSPACE_ROOT / "outputs"

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

    # Run overall counterfactual attribution against observed slick (Commit 7 Vector & Physical Shape Consistency)
    attribution_scenario = {
        "observation": {
            "time": OBSERVED_SLICK["time"],
            "centroid": OBSERVED_SLICK["centroid"],
            "footprint_geojson": {
                "type": "Polygon",
                "coordinates": [[
                    [72.58, 18.86],
                    [72.62, 18.86],
                    [72.62, 18.90],
                    [72.58, 18.90],
                    [72.58, 18.86]
                ]]
            }
        },
        "analysis": {
            "min_hours_before": 3,
            "max_hours_before": 8,
            "run_count": 80,
            "match_radius_m": 6000,
            "minimum_consistency_fraction": 0.40,
            "minimum_vector_score": 0.40,
            "vector_weights": {
                "centroid_fraction": 0.4,
                "polygon_support_fraction": 0.3,
                "area_similarity": 0.15,
                "orientation_similarity": 0.15,
                "orientation_minimum_anisotropy": 0.15,
            },
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
    for cand in attribution_results.get("candidates", []):
        rhs = cand.get("release_hypotheses", [])
        if rhs and "physical_consistency_vector" in rhs[0]:
            cand["physical_consistency_vector"] = rhs[0]["physical_consistency_vector"]

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

        # Operational response queue for this ship's impact forecast (Commit 4)
        ship_response = build_response_queue(
            impact_forecast,
            {
                "rules": [
                    {
                        "rule_id": "rule_high_exposure_sensitive",
                        "priority_rank": 1,
                        "conditions": [
                            {"field": "consequence_weight", "operator": "gte", "value": 0.8},
                            {"field": "exposure_fraction", "operator": "gte", "value": 0.35}
                        ],
                        "actions": [
                            "Predeploy containment boom perimeter",
                            "Deploy skimmer taskforce from Mumbai offshore base",
                            "Alert marine sanctuary reserve management"
                        ]
                    },
                    {
                        "rule_id": "rule_imminent_intercept",
                        "priority_rank": 2,
                        "conditions": [
                            {"field": "earliest_eta_hours", "operator": "lte", "value": 12.0},
                            {"field": "exposure_fraction", "operator": "gte", "value": 0.15}
                        ],
                        "actions": [
                            "Issue coastal intertidal patrol notification",
                            "Request updated high-resolution SAR satellite observation"
                        ]
                    },
                    {
                        "rule_id": "rule_general_monitoring",
                        "priority_rank": 3,
                        "conditions": [
                            {"field": "exposure_fraction", "operator": "gte", "value": 0.05}
                        ],
                        "actions": [
                            "Maintain automated drift trajectory monitoring"
                        ]
                    }
                ]
            }
        )

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
            "response_queue": ship_response,
        }
        ships_output.append(ship_obj)

    # Rank surveillance queue
    ranked_queue = sorted(
        [s["surveillance"] for s in ships_output],
        key=lambda x: x["priority_index"],
        reverse=True,
    )

    primary_ship = ships_output[0]

    # === COMMIT 3: Dark Vessel Dead Reckoning vs. SAR ===
    dead_reckoning = {}
    dr_path = SCENARIOS_DIR / "dead_reckoning_demo.json"
    if dr_path.exists():
        dr_case = json.loads(dr_path.read_text(encoding="utf-8-sig"))
        dead_reckoning = assess_gap_detections(dr_case)

    # === SAR / AIS Cross-Verification (AIS Trust) ===
    ais_trust = {}
    at_path = SCENARIOS_DIR / "ais_trust_demo.json"
    if at_path.exists():
        at_case = json.loads(at_path.read_text(encoding="utf-8-sig"))
        ais_trust = verify_sar_ais(at_case)

    # === COMMIT 3: Bayesian Forecast Update ===
    forecast_update = {}
    fu_path = SCENARIOS_DIR / "forecast_update_demo.json"
    if fu_path.exists():
        fu_case = json.loads(fu_path.read_text(encoding="utf-8-sig"))
        forecast_update = update_forecast(fu_case)

    # === COMMIT 4: Observation Window Planner ===
    observation_plan = {}
    op_path = SCENARIOS_DIR / "observation_plan_demo.json"
    if op_path.exists():
        op_case = json.loads(op_path.read_text(encoding="utf-8-sig"))
        observation_plan = rank_observation_windows(op_case)

    # === COMMIT 5: AIS Data Integrity Inspection ===
    demo_integrity_path = SCENARIOS_DIR / "ais_integrity_demo.json"
    demo_tracks = []
    if demo_integrity_path.exists():
        demo_tracks = json.loads(demo_integrity_path.read_text(encoding="utf-8-sig")).get("tracks", [])

    integrity_case = {
        "settings": {
            "earth_radius_m": 6371008.8,
            "meters_per_nautical_mile": 1852.0,
            "seconds_per_hour": 3600.0,
            "max_course_change_interval_seconds": 900,
            "course_reversal_threshold_deg": 120.0,
            "frozen_coordinate_tolerance_m": 50.0,
            "frozen_minimum_points": 3,
        },
        "speed_limits_knots": {
            "tanker": 18.0,
            "cargo": 19.0,
            "container": 23.0,
        },
        "tracks": [
            {
                "mmsi": s["mmsi"],
                "vessel_type": s["type"],
                "points": [
                    {"time": p["time"], "lat": p["lat"], "lon": p["lon"], "cog_degrees": p.get("cog_deg")}
                    for p in s["ais_points"]
                ],
            }
            for s in SHIPS_SPEC
        ] + demo_tracks,
    }
    fleet_integrity = inspect_ais_integrity(integrity_case)

    # Attach specific integrity flags to each ship
    for s in ships_output:
        s["integrity_flags"] = [
            e for e in fleet_integrity["events"] if e.get("mmsi") == s["mmsi"]
        ]

    # === COMMIT 5: Temporal Risk Decay ===
    temporal_risk = {}
    tr_path = SCENARIOS_DIR / "temporal_risk_demo.json"
    if tr_path.exists():
        tr_case = json.loads(tr_path.read_text(encoding="utf-8-sig"))
        temporal_risk = calculate_temporal_risk(tr_case)

    # === COMMIT 5: Unified Investigation Timeline ===
    timeline_path = SCENARIOS_DIR / "investigation_timeline_demo.json"
    investigation_timeline = {"events": []}
    if timeline_path.exists():
        tl_case = json.loads(timeline_path.read_text(encoding="utf-8-sig"))
        raw_tl = build_investigation_timeline(tl_case)
        investigation_timeline = merge_integrity_flags(raw_tl, fleet_integrity)

    # === COMMIT 5: Investigation Dossier HTML ===
    dossier_html = ""
    dossier_file = OUTPUTS_DIR / "investigation_dossier.html"
    if dossier_file.exists():
        dossier_html = dossier_file.read_text(encoding="utf-8")

    # === COMMIT 6: Contextual Behavior Engine ===
    contextual_behavior = {}
    cb_path = SCENARIOS_DIR / "contextual_behavior_demo.json"
    if cb_path.exists():
        cb_case = json.loads(cb_path.read_text(encoding="utf-8-sig"))
        contextual_behavior = score_contextual_behavior(cb_case)

    # === COMMIT 7: Jurisdictional Escape & Intercept Feasibility ===
    escape_intercept = {}
    ei_path = SCENARIOS_DIR / "escape_intercept_demo.json"
    if ei_path.exists():
        ei_case = json.loads(ei_path.read_text(encoding="utf-8-sig"))
        escape_intercept = analyze_escape_intercept(ei_case)

    # === COMMIT 8: Complete Investigation Timeline Fusion ===
    try:
        if investigation_timeline and temporal_risk:
            investigation_timeline = merge_surveillance_timeline(
                deepcopy(investigation_timeline),
                temporal_risk,
                {"queue": ranked_queue},
                contextual_behavior if contextual_behavior else None,
            )
    except Exception as e:
        print(f"Timeline merge warning: {e}")

    return {
        "active_case": OBSERVED_SLICK,
        "ships": ships_output,
        "selected_mmsi": primary_ship["mmsi"],
        "overall_attribution": attribution_results,
        "dead_reckoning": dead_reckoning,
        "ais_trust": ais_trust,
        "observation_plan": observation_plan,
        "forecast_update": forecast_update,
        "ais_integrity": fleet_integrity,
        "temporal_risk": temporal_risk,
        "investigation_timeline": investigation_timeline,
        "dossier_html": dossier_html,
        "overall_response_queue": primary_ship.get("response_queue", {}),
        "contextual_behavior": contextual_behavior,
        "escape_intercept": escape_intercept,
        # Backward compatibility with existing frontend types
        "vessel_analysis": primary_ship["vessel_analysis"],
        "drift_analysis": {
            "forward_track": primary_ship["drift_forecast"]["forward_track"],
            "hindcast_origins": primary_ship["drift_backtrack"]["hindcast"],
        },
        "attribution": attribution_results,
        "surveillance_queue": ranked_queue,
    }

