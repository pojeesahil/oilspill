import json
import math
import sys
from pathlib import Path


def find_baseline(observation, baselines):
    matches = [
        baseline for baseline in baselines
        if all(observation.get(key) == value
               for key, value in baseline["match"].items())
    ]

    if not matches:
        raise ValueError(
            "No baseline matches vessel "
            f"{observation.get('mmsi')} in "
            f"{observation.get('operating_context')}"
        )

    specificity = max(len(item["match"]) for item in matches)
    best = [item for item in matches if len(item["match"]) == specificity]

    if len(best) != 1:
        raise ValueError(
            f"Multiple equally specific baselines match "
            f"{observation.get('mmsi')}"
        )

    return best[0]


def score_scenario(scenario):
    config = scenario["scoring"]
    threshold = float(config["zscore_threshold"])
    saturation = float(config["saturation_zscore"])
    event_type = config["event_type"]

    if threshold < 0 or saturation <= threshold:
        raise ValueError(
            "saturation_zscore must be greater than "
            "a non-negative zscore_threshold"
        )

    vessel_results = {}
    scored_observations = []

    for observation in scenario["observations"]:
        baseline = find_baseline(observation, scenario["baselines"])
        metric_signals = {}
        remaining = 1.0

        for name, value in observation["metrics"].items():
            if name not in baseline["metrics"]:
                raise ValueError(
                    f"Baseline has no metric '{name}' for "
                    f"{observation['mmsi']}"
                )

            reference = baseline["metrics"][name]
            mean = float(reference["mean"])
            std = float(reference["std"])

            if std <= 0:
                raise ValueError(
                    f"Baseline standard deviation for '{name}' must be positive"
                )

            zscore = (float(value) - mean) / std
            severity = max(
                0.0,
                min(1.0, (abs(zscore) - threshold) /
                    (saturation - threshold))
            )
            remaining *= 1.0 - severity

            metric_signals[name] = {
                "observed": float(value),
                "baseline_mean": mean,
                "baseline_std": std,
                "standardized_deviation": round(zscore, 3),
                "severity": round(severity, 4),
            }

        contextual_score = round(1.0 - remaining, 4)
        reasons = [
            name for name, signal in metric_signals.items()
            if signal["severity"] > 0
        ]

        result = {
            "mmsi": observation["mmsi"],
            "time": observation["time"],
            "operating_context": observation["operating_context"],
            "contextual_behavior_index": contextual_score,
            "reasons": reasons,
            "metric_signals": metric_signals,
        }
        scored_observations.append(result)

        if reasons:
            vessel = vessel_results.setdefault(
                observation["mmsi"],
                {"mmsi": observation["mmsi"], "events": []},
            )
            vessel["events"].append({
                "time": observation["time"],
                "type": event_type,
                "severity": contextual_score,
                "reasons": reasons,
            })

    return {
        "vessels": list(vessel_results.values()),
        "observations": scored_observations,
        "score_meaning": (
            "Configured deviation from supplied vessel and context baselines. "
            "Baseline quality affects results; this is not a spill probability "
            "or evidence of intent."
        ),
    }


def main():
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: python -m backend.vessels.contextual_behavior SCENARIO.json"
        )

    scenario = json.loads(
        Path(sys.argv[1]).read_text(encoding="utf-8-sig")
    )
    print(json.dumps(score_scenario(scenario), indent=2))


if __name__ == "__main__":
    main()