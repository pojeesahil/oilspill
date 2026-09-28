import argparse
import json
from pathlib import Path

from oilspill.api.backend.ocean.drift import (
    DriftConfig,
    DriftForcing,
    monte_carlo_hindcast,
    simulate_drift,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario_path")
    args = parser.parse_args()

    scenario_path = Path(args.scenario_path)
    scenario = json.loads(scenario_path.read_text(encoding="utf-8-sig"))

    forcing = DriftForcing(**scenario["forcing"])
    config = DriftConfig(**scenario["physics"])
    release = scenario["hypothetical_release"]
    observed = scenario["observed_spill"]
    duration_hours = scenario["duration_hours"]
    monte_carlo = scenario["monte_carlo"]

    forward_track = simulate_drift(
        lat=release["lat"],
        lon=release["lon"],
        start_time=release["time"],
        duration_hours=duration_hours,
        forcing=forcing,
        config=config,
        direction=1,
        seed=monte_carlo["seed"],
    )

    origin_estimate = monte_carlo_hindcast(
        observed_lat=observed["lat"],
        observed_lon=observed["lon"],
        observed_time=observed["time"],
        min_hours_before=monte_carlo["min_hours_before"],
        max_hours_before=monte_carlo["max_hours_before"],
        run_count=monte_carlo["run_count"],
        forcing=forcing,
        config=config,
        lower_quantile=monte_carlo["lower_quantile"],
        upper_quantile=monte_carlo["upper_quantile"],
        seed=monte_carlo["seed"],
    )

    print(f"Case: {scenario['case_id']}")
    print(f"Data status: {scenario['data_status']}")
    print(f"Forward endpoint: {json.dumps(forward_track[-1])}")
    print(f"Hindcast runs: {origin_estimate['run_count']}")
    print(f"Origin percentile bounds: {json.dumps(origin_estimate['bounds'])}")
    print(f"Sample origins: {json.dumps(origin_estimate['origins'][:5])}")


if __name__ == "__main__":
    main()