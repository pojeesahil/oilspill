import os
import json
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from backend.vessels.surveillance import analyze_track
from backend.ocean.drift import simulate_drift, monte_carlo_hindcast, DriftForcing, DriftConfig
from backend.forensics.counterfactual import evaluate_counterfactuals
from backend.environment.impact import forecast_hypothetical_impact
from backend.environment.opportunity import calculate_spill_opportunity
from backend.environment.uncertainty import calculate_data_uncertainty
from backend.environment.priority import calculate_surveillance_priority
from backend.environment.pre_spill import evaluate_pre_spill_candidate, rank_surveillance_candidates

app = FastAPI(title="SIH 143 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

WORKSPACE_ROOT = r"c:\Users\sahil\Documents\antig\sih143\we_have_to_win_sih"
SCENARIOS_DIR = os.path.join(WORKSPACE_ROOT, "scenarios")

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

@app.post("/api/vessel/analyze")
async def analyze_vessel(request: Request):
    case = await request.json()
    try:
        return analyze_track(case)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/drift/forward")
async def drift_forward(request: Request):
    data = await request.json()
    try:
        forcing = DriftForcing(**data.get("forcing", {}))
        config = DriftConfig(**data.get("config", {}))
        return simulate_drift(
            lat=data["lat"],
            lon=data["lon"],
            start_time=data["start_time"],
            duration_hours=data["duration_hours"],
            forcing=forcing,
            config=config,
            direction=1,
            seed=data.get("seed", 42)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/drift/hindcast")
async def drift_hindcast(request: Request):
    data = await request.json()
    try:
        forcing = DriftForcing(**data.get("forcing", {}))
        config = DriftConfig(**data.get("config", {}))
        return monte_carlo_hindcast(
            observed_lat=data["observed_lat"],
            observed_lon=data["observed_lon"],
            observed_time=data["observed_time"],
            min_hours_before=data["min_hours_before"],
            max_hours_before=data["max_hours_before"],
            run_count=data["run_count"],
            forcing=forcing,
            config=config,
            lower_quantile=data.get("lower_quantile", 0.05),
            upper_quantile=data.get("upper_quantile", 0.95),
            seed=data.get("seed", 42)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/forensics/attribution")
async def forensics_attribution(request: Request):
    scenario = await request.json()
    try:
        return evaluate_counterfactuals(scenario)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/environment/impact")
async def environment_impact(request: Request):
    case = await request.json()
    try:
        return forecast_hypothetical_impact(case)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/surveillance/priority")
async def surveillance_priority(request: Request):
    data = await request.json()
    candidates = data.get("candidates", [])
    try:
        evaluated = []
        for cand in candidates:
            opportunity = calculate_spill_opportunity(
                cand["opportunity"]["signals"],
                cand["opportunity"]["weights"],
            )
            uncertainty = calculate_data_uncertainty(
                cand["uncertainty"]["signals"],
                cand["uncertainty"]["weights"],
            )
            impact = forecast_hypothetical_impact(cand["impact_case"])

            behavior_index = cand["behavior_index"]
            spill_opportunity = opportunity["spill_opportunity"]
            data_uncertainty_val = uncertainty["data_uncertainty"]
            impact_index = impact["impact_index"]

            incident_proxy = behavior_index * spill_opportunity
            priority_index = incident_proxy * impact_index * data_uncertainty_val

            evaluated.append({
                "mmsi": cand["mmsi"],
                "behavior_index": behavior_index,
                "spill_opportunity": spill_opportunity,
                "potential_impact_index": impact_index,
                "data_uncertainty": data_uncertainty_val,
                "incident_proxy": incident_proxy,
                "priority_index": priority_index,
                "impact_forecast": impact,
                "score_meaning": (
                    "Prototype surveillance ranking index; not a spill probability "
                    "or attribution score."
                ),
            })
        ranked = rank_surveillance_candidates(evaluated)
        return ranked
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/scenarios/{name}")
def get_scenario(name: str):
    allowed = ["ais_demo", "drift_demo", "attribution_demo", "surveillance_demo"]
    if name not in allowed:
        raise HTTPException(status_code=404, detail="Scenario not found")
    filepath = os.path.join(SCENARIOS_DIR, f"{name}.json")
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")
    with open(filepath, "r", encoding="utf-8-sig") as f:
        return json.load(f)

from api.ships_service import compute_multi_ship_data

_CACHED_ANALYSIS = None

def get_or_compute_analysis():
    global _CACHED_ANALYSIS
    if _CACHED_ANALYSIS is None:
        _CACHED_ANALYSIS = compute_multi_ship_data()
    return _CACHED_ANALYSIS

@app.get("/api/ships")
def list_ships():
    """List all tracked ships with their telemetry and drift summaries."""
    data = get_or_compute_analysis()
    return data["ships"]

@app.get("/api/ships/{mmsi}")
def get_ship(mmsi: str):
    """Get full details, forecast, and backtrack for a specific ship."""
    data = get_or_compute_analysis()
    ship = next((s for s in data["ships"] if s["mmsi"] == mmsi), None)
    if not ship:
        raise HTTPException(status_code=404, detail=f"Ship {mmsi} not found")
    return ship

@app.post("/api/demo/refresh")
def refresh_analysis():
    """Recompute all simulations and refresh cache."""
    global _CACHED_ANALYSIS
    _CACHED_ANALYSIS = compute_multi_ship_data()
    return {"status": "refreshed", "ships_count": len(_CACHED_ANALYSIS["ships"])}

@app.get("/api/demo/full-analysis")
def full_analysis():
    """Returns multi-ship intelligence with individual forecasts and backtracks."""
    try:
        return get_or_compute_analysis()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

