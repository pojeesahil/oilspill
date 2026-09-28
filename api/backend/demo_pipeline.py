"""Run the complete synthetic PS-143 simulation demo and save judge-readable outputs."""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from oilspill.api.backend.environment.contextual_queue import add_contextual_events
from oilspill.api.backend.environment.dynamic_queue import build_dynamic_queue
from oilspill.api.backend.environment.escape_intercept import analyze as analyze_escape
from oilspill.api.backend.environment.impact import forecast_hypothetical_impact
from oilspill.api.backend.environment.opportunity import calculate_spill_opportunity
from oilspill.api.backend.environment.pre_spill import evaluate_pre_spill_candidate
from oilspill.api.backend.environment.response import build_response_queue
from oilspill.api.backend.environment.uncertainty import calculate_data_uncertainty
from oilspill.api.backend.forensics.ais_trust import verify_sar_ais
from oilspill.api.backend.forensics.counterfactual import evaluate_counterfactuals
from oilspill.api.backend.forensics.dead_reckoning import assess_gap_detections
from oilspill.api.backend.forensics.dossier import make_dossier
from oilspill.api.backend.forensics.evidence import build_hypothesis_report
from oilspill.api.backend.forensics.merge_counterfactual_timeline import (
    merge_counterfactual_timeline,
)
from oilspill.api.backend.forensics.merge_integrity_timeline import merge_integrity_flags
from oilspill.api.backend.forensics.merge_surveillance_timeline import (
    merge_surveillance_timeline,
)
from oilspill.api.backend.forensics.timeline import build_investigation_timeline
from oilspill.api.backend.ocean.drift import DriftConfig, DriftForcing, monte_carlo_hindcast
from oilspill.api.backend.ocean.forecast_update import update_forecast
from oilspill.api.backend.ocean.observation_planner import rank_observation_windows
from oilspill.api.backend.vessels.contextual_behavior import score_scenario
from oilspill.api.backend.vessels.integrity import inspect_ais_integrity
from oilspill.api.backend.vessels.temporal_risk import calculate_temporal_risk

SCENARIOS = PROJECT_ROOT / "scenarios"
OUTPUTS = PROJECT_ROOT / "outputs" / "synthetic_integrated_demo"


def read_scenario(name):
    return json.loads((SCENARIOS / name).read_text(encoding="utf-8-sig"))


def save(name, value):
    (OUTPUTS / name).write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main():
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    manifest = {
        "scenario_label": "SYNTHETIC SIMULATION — not live data or operational output",
        "sar_observation": "Supplied synthetic GeoJSON footprint and centroid; no detector or ML model used.",
        "ais_tracks": "Supplied synthetic vessel tracks.",
        "environmental_forcing_and_ecosystems": "Scenario-configured synthetic forcing and zones.",
        "score_caveat": "Indices/fractions are configured simulation outputs, not calibrated probabilities, guilt scores, live detections, or operational forecasts.",
        "pipeline": [],
    }

    # 1. Pre-spill: context-specific behavior -> decayed signals -> consequences -> queue.
    contextual = score_scenario(read_scenario("contextual_behavior_demo.json"))
    save("contextual_behavior.json", contextual)
    temporal_scenario = read_scenario("temporal_risk_demo.json")
    add_contextual_events(temporal_scenario, contextual)
    temporal = calculate_temporal_risk(temporal_scenario)
    save("temporal_risk.json", temporal)

    surveillance_scenario = read_scenario("surveillance_demo.json")
    base_queue = []
    evaluated = []
    contextual_max = max(
        (item["contextual_behavior_index"] for item in contextual["observations"]),
        default=0.0,
    )
    for candidate in surveillance_scenario["candidates"]:
        impact_case = copy.deepcopy(candidate["impact_case"])
        opportunity = calculate_spill_opportunity(
            candidate["opportunity"]["signals"],
            candidate["opportunity"]["weights"],
        )["spill_opportunity"]
        uncertainty = calculate_data_uncertainty(
            candidate["uncertainty"]["signals"],
            candidate["uncertainty"]["weights"],
        )["data_uncertainty"]
        result = evaluate_pre_spill_candidate(
            mmsi=candidate["mmsi"],
            behavior_index=contextual_max,
            spill_opportunity=opportunity,
            data_uncertainty=uncertainty,
            impact_case=impact_case,
        )
        evaluated.append(result)
        base_queue.append({
            "mmsi": candidate["mmsi"],
            "behavior_index": result["behavior_index"],
            "spill_opportunity": result["spill_opportunity"],
            "potential_impact_index": result["potential_impact_index"],
            "data_uncertainty": result["data_uncertainty"],
            "impact_forecast": result["impact_forecast"],
        })
    temporal_queue = build_dynamic_queue(
        {"scenario_label": surveillance_scenario["scenario_label"], "queue": base_queue},
        temporal,
    )
    save("consequence_aware_priority.json", temporal_queue)
    manifest["pipeline"].append(
        "contextual baseline → temporal decay → consequence-aware surveillance priority"
    )

    # 2. AIS & SAR sensor integrity, trust cross-check, dead reckoning, and EEZ escape/intercept.
    ais_integrity = inspect_ais_integrity(read_scenario("ais_integrity_demo.json"))
    save("ais_integrity.json", ais_integrity)

    ais_trust = verify_sar_ais(read_scenario("ais_trust_demo.json"))
    save("ais_trust.json", ais_trust)

    dead_reckoning = assess_gap_detections(read_scenario("dead_reckoning_demo.json"))
    save("dead_reckoning.json", dead_reckoning)

    escape_intercept = analyze_escape(read_scenario("escape_intercept_demo.json"))
    save("escape_intercept.json", escape_intercept)

    manifest["pipeline"].append(
        "AIS kinematic/integrity screening → SAR-AIS trust cross-check → dead reckoning gap analysis → EEZ escape & patrol intercept vector"
    )

    # 3. Post-spill: Monte-Carlo backward hindcast + counterfactual release simulations.
    attribution_scenario = read_scenario("attribution_demo.json")
    forcing = DriftForcing(**attribution_scenario["forcing"])
    config = DriftConfig(**attribution_scenario["drift_config"])
    hindcast_result = monte_carlo_hindcast(
        observed_lat=attribution_scenario["observation"]["centroid"]["lat"],
        observed_lon=attribution_scenario["observation"]["centroid"]["lon"],
        observed_time=attribution_scenario["observation"]["time"],
        min_hours_before=attribution_scenario["analysis"]["min_hours_before"],
        max_hours_before=attribution_scenario["analysis"]["max_hours_before"],
        run_count=attribution_scenario["analysis"]["run_count"],
        forcing=forcing,
        config=config,
        lower_quantile=0.05,
        upper_quantile=0.95,
        seed=attribution_scenario["analysis"]["random_seed"],
    )
    hindcast_result["scenario_label"] = "SYNTHETIC HINDCAST ENVELOPE"
    hindcast_result["score_meaning"] = (
        "Synthetic simulation output. Sampled origins and coordinate bounds "
        "represent a prototype hindcast envelope under scenario forcing uncertainty. "
        "They are not calibrated probabilities, probability heatmaps, or 50/80/95% "
        "validated confidence regions."
    )
    save("origin_reconstruction.json", hindcast_result)

    counterfactual = evaluate_counterfactuals(attribution_scenario)
    save("counterfactual.json", counterfactual)
    evidence = build_hypothesis_report(counterfactual, {
        row["mmsi"]: {"contextual_behavior_index": contextual_max}
        for row in contextual["observations"]
    })
    save("evidence_fusion.json", evidence)

    negative_case = read_scenario("attribution_none_demo.json")
    negative_result = evaluate_counterfactuals(negative_case)
    save("negative_control_evidence.json", build_hypothesis_report(negative_result))
    manifest["sar_observation"] += (
        " Counterfactual attribution tests synthetic release hypotheses against centroid and footprint geometry."
    )
    manifest["pipeline"].append(
        "synthetic SAR centroid → Monte-Carlo backward hindcast origin envelope → counterfactual release simulation → centroid + vector evidence fusion → unknown-source review"
    )

    # 4. New synthetic observation updates a forecast ensemble; planner recommends which next window separates hypotheses.
    forecast_case = read_scenario("forecast_update_demo.json")
    forecast_case["observation"]["time"] = attribution_scenario["observation"]["time"]
    forecast_case["observation"].update(attribution_scenario["observation"]["centroid"])
    forecast_update = update_forecast(forecast_case)
    observation_plan = rank_observation_windows(read_scenario("observation_plan_demo.json"))
    save("forecast_correction.json", forecast_update)
    save("observation_plan.json", observation_plan)
    manifest["pipeline"].append(
        "new synthetic observation → forecast ensemble correction → next observation window ranking"
    )

    # 5. Post-spill: forecast impact from the synthetic SAR centroid; keep this distinct
    # from pre-spill hypothetical-vessel impact used for surveillance priority.
    post_spill_impact_case = copy.deepcopy(surveillance_scenario["candidates"][0]["impact_case"])
    post_spill_impact_case["release"] = copy.deepcopy(attribution_scenario["observation"]["centroid"])
    post_spill_impact_case["ecosystem_zones"]["features"][0]["geometry"] = {
        "type": "Polygon",
        "coordinates": [[
            [72.65, 18.82], [72.80, 18.82], [72.80, 18.95],
            [72.65, 18.95], [72.65, 18.82],
        ]],
    }
    impact_forecast = forecast_hypothetical_impact(post_spill_impact_case)
    save("post_spill_impact.json", impact_forecast)
    response_policy = read_scenario("response_demo.json")["policy"]
    response = build_response_queue(impact_forecast, response_policy)
    save("response_recommendations.json", response)
    manifest["pipeline"].append(
        "pre-spill hypothetical impact → surveillance priority; post-spill SAR-centroid impact → configured response recommendations"
    )

    # 6. Merge pre-spill context, AIS/SAR integrity, and post-spill evidence into one explicitly role-labeled timeline.
    timeline_case = read_scenario("investigation_timeline_demo.json")
    timeline_case["counterfactual_result"] = counterfactual
    timeline_case["response_result"] = response
    timeline = build_investigation_timeline(timeline_case)
    timeline = merge_surveillance_timeline(
        timeline,
        temporal,
        temporal_queue,
        contextual,
    )
    timeline = merge_counterfactual_timeline(timeline, counterfactual)
    timeline = merge_integrity_flags(timeline, ais_integrity)

    observed_time = timeline_case["observed_spill"]["time"]
    timeline["events"].append({
        "time": attribution_scenario["observation"]["time"],
        "type": "probabilistic_origin_reconstruction",
        "title": "Monte-Carlo backward hindcast origin envelope generated",
        "details": f"{hindcast_result['run_count']} synthetic runs; lat bounds: [{hindcast_result['bounds']['lat'][0]:.4f}, {hindcast_result['bounds']['lat'][1]:.4f}], lon bounds: [{hindcast_result['bounds']['lon'][0]:.4f}, {hindcast_result['bounds']['lon'][1]:.4f}].",
        "evidence_role": "Synthetic Monte-Carlo backward drift hindcast envelope; simulation proxy, not a validated probability distribution.",
    })

    for match in ais_trust.get("matches", []):
        timeline["events"].append({
            "time": ais_trust.get("sar_acquisition_time", observed_time),
            "type": "sar_ais_cross_check_match",
            "title": f"SAR-AIS sensor cross-check match: {match['mmsi']}",
            "details": f"Detection {match['detection_id']}; distance: {match['distance_m']} m; time delta: {match['time_delta_seconds']} s.",
            "evidence_role": "Spatial-temporal sensor cross-check; not an identity authentication.",
        })
    for detection in ais_trust.get("unmatched_sar_detections", []):
        timeline["events"].append({
            "time": ais_trust.get("sar_acquisition_time", observed_time),
            "type": "unmatched_sar_detection",
            "title": f"Unmatched SAR detection: {detection['detection_id']}",
            "details": f"Lat: {detection['lat']}, Lon: {detection['lon']}. Possible unreported vessel or detection clutter.",
            "evidence_role": "Sensor anomaly review; not proof of a dark vessel.",
        })

    for match in dead_reckoning.get("matches", []):
        timeline["events"].append({
            "time": observed_time,
            "type": "dead_reckoning_match",
            "title": f"Dead reckoning corridor match: {match['mmsi']}",
            "details": f"Predicted distance to detection {match['detection_id']}: {match['detection_distance_m']} m (corridor radius: {match['corridor_radius_m']} m).",
            "evidence_role": "Position projection during AIS gap; candidate association only.",
        })

    if escape_intercept.get("projected_boundary_exit"):
        exit_info = escape_intercept["projected_boundary_exit"]
        timeline["events"].append({
            "time": exit_info["time"],
            "type": "projected_eez_exit",
            "title": f"Projected EEZ boundary exit: {escape_intercept['vessel_id']}",
            "details": f"ETA: {exit_info['eta_hours']:.2f} h at lat {exit_info['position']['lat']:.4f}, lon {exit_info['position']['lon']:.4f}.",
            "evidence_role": "Constant-course boundary projection estimate; not an operational tracking forecast.",
        })
    if escape_intercept.get("interception_estimate"):
        intercept_info = escape_intercept["interception_estimate"]
        timeline["events"].append({
            "time": intercept_info["time"],
            "type": "patrol_interception_vector",
            "title": f"Patrol intercept vector from {intercept_info['base']}",
            "details": f"Target time: {intercept_info['vessel_eta_hours']:.2f} h; Patrol ETA: {intercept_info['patrol_eta_hours']:.2f} h (margin: {intercept_info['time_margin_hours']:.2f} h).",
            "evidence_role": "Calculated intercept vector recommendation; not a live dispatch.",
        })

    plan = observation_plan.get("recommended_observation_window")
    if plan:
        timeline["events"].append({
            "time": plan["time"],
            "type": "recommended_observation_window",
            "title": "Recommended next observation window",
            "details": f"Top heuristic separation score: {plan['separation_score']:.3f}",
            "evidence_role": "Synthetic forecast-based observation planning; recommendation only.",
        })
    for zone in response["response_queue"]:
        timeline["events"].append({
            "time": observed_time,
            "type": "response_recommendation",
            "title": f"Response rule outcome: {zone['zone']}",
            "details": "; ".join(zone.get("recommended_actions", [])) or f"Status: {zone['status']}; no action rule triggered.",
            "evidence_role": "Configured post-spill response rule outcome; not a recorded operational action.",
        })
    timeline["events"].append({
        "time": observed_time,
        "type": "forecast_correction",
        "title": "Forecast ensemble corrected by synthetic observation",
        "details": "Posterior weights and corrected forecast use scenario-supplied observation uncertainty.",
        "evidence_role": "Synthetic forecast update; not an operational forecast.",
    })
    timeline["events"].sort(key=lambda event: event.get("time", ""))
    save("unified_timeline.json", timeline)

    dossier = make_dossier(evidence, timeline, temporal_queue, response)
    (OUTPUTS / "investigation_dossier.html").write_text(dossier, encoding="utf-8")
    manifest["pipeline"].append("single merged timeline + HTML investigation dossier (not PDF)")
    save("demo_manifest.json", manifest)
    print(f"Synthetic integrated demo complete: {OUTPUTS}")
    print(f"Events: {len(timeline['events'])}; candidates: {len(counterfactual['candidates'])}; response zones: {len(response['response_queue'])}")
    print("All outputs are synthetic simulation results; see demo_manifest.json for limits.")


if __name__ == "__main__":
    main()
