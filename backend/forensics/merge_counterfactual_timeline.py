"""Add vector counterfactual results to an existing investigation timeline."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


INTERPRETATION = (
    "Counterfactual values describe physical consistency under the configured "
    "scenario. They are not guilt scores, source probabilities, or legal attribution."
)


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def _time_key(value):
    if not value:
        return ""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat()
    except (AttributeError, TypeError, ValueError):
        return str(value)


def _event_time(timeline):
    for event in timeline.get("events", []):
        if event.get("type") == "sar_spill_observation" and event.get("time"):
            return event["time"]

    event_times = [
        event.get("time")
        for event in timeline.get("events", [])
        if event.get("time")
    ]
    return max(event_times, key=_time_key) if event_times else None


def _find_candidate(timeline, counterfactual):
    candidates = counterfactual.get("candidates", [])
    timeline_mmsi = timeline.get("mmsi")

    if timeline_mmsi:
        matches = [
            candidate
            for candidate in candidates
            if candidate.get("mmsi") == timeline_mmsi
        ]
        if matches:
            return matches[0]

    if len(candidates) == 1:
        return candidates[0]

    raise ValueError(
        "Could not select a counterfactual candidate for this timeline. "
        "Set timeline.mmsi to one of the candidate MMSIs."
    )


def _release_record(hypothesis):
    vector = hypothesis.get("physical_consistency_vector", {})
    return {
        "release_time": hypothesis.get("release_time"),
        "centroid_consistency_fraction": hypothesis.get("ensemble_consistency"),
        "physical_consistency_score": vector.get(
            "physical_consistency_score"
        ),
        "physical_consistency_vector": vector,
        "simulations": hypothesis.get("simulations"),
    }


def _insert_or_update_release_events(timeline, candidate, counterfactual):
    events = timeline.setdefault("events", [])
    hypotheses = candidate.get("release_hypotheses", [])

    by_time = {
        _time_key(hypothesis.get("release_time")): hypothesis
        for hypothesis in hypotheses
        if hypothesis.get("release_time")
    }
    matched = set()

    for event in events:
        if event.get("type") not in {
            "hypothetical_release_test",
            "counterfactual_release_test",
        }:
            continue

        key = _time_key(event.get("time") or event.get("release_time"))
        hypothesis = by_time.get(key)
        if hypothesis is None:
            continue

        matched.add(key)
        record = _release_record(hypothesis)
        event.update(record)
        event["configured_centroid_threshold"] = counterfactual.get(
            "threshold_used"
        )
        event["configured_vector_threshold"] = counterfactual.get(
            "vector_threshold_used"
        )

        score = record.get("physical_consistency_score")
        vector_threshold = counterfactual.get("vector_threshold_used")
        event["vector_threshold_met"] = (
            score is not None
            and vector_threshold is not None
            and score >= vector_threshold
        )
        event["evidence_role"] = (
            "Counterfactual physical-consistency test."
        )
        event["interpretation"] = INTERPRETATION

    for key, hypothesis in by_time.items():
        if key in matched:
            continue

        record = _release_record(hypothesis)
        events.append({
            "time": hypothesis["release_time"],
            "type": "hypothetical_release_test",
            "title": (
                "Release-time hypothesis tested for "
                f"{candidate.get('mmsi', 'candidate')}"
            ),
            **record,
            "configured_centroid_threshold": counterfactual.get(
                "threshold_used"
            ),
            "configured_vector_threshold": counterfactual.get(
                "vector_threshold_used"
            ),
            "evidence_role": "Counterfactual physical-consistency test.",
            "interpretation": INTERPRETATION,
        })


def _add_candidate_summary(timeline, candidate, counterfactual):
    events = timeline.setdefault("events", [])
    summary_type = "counterfactual_candidate_summary"

    # Replace an earlier summary so rerunning this merge stays safe.
    events[:] = [
        event for event in events
        if event.get("type") != summary_type
    ]

    score = candidate.get("physical_consistency_score")
    centroid_fraction = candidate.get("physical_consistency_fraction")
    vector_threshold = counterfactual.get("vector_threshold_used")

    if score is None:
        status = "insufficient_candidate_track_data"
        detail = (
            "No usable candidate simulations were available in the "
            "configured time window."
        )
    elif vector_threshold is not None and score >= vector_threshold:
        status = "meets_configured_vector_threshold"
        detail = (
            "The candidate met the configured physical-consistency test; "
            "this does not establish source identity."
        )
    else:
        status = "below_configured_vector_threshold"
        detail = (
            "The candidate did not meet the configured physical-consistency "
            "test; this does not rule out other or untracked sources."
        )

    events.append({
        "time": _event_time(timeline),
        "type": summary_type,
        "title": (
            f"Counterfactual assessment for "
            f"{candidate.get('mmsi', 'candidate')}"
        ),
        "status": status,
        "physical_consistency_fraction": centroid_fraction,
        "physical_consistency_score": score,
        "configured_centroid_threshold": counterfactual.get(
            "threshold_used"
        ),
        "configured_vector_threshold": vector_threshold,
        "evidence_role": (
            "Post-incident physical-consistency evidence; surveillance "
            "signals are not counted as causal evidence."
        ),
        "details": detail,
        "interpretation": INTERPRETATION,
    })


def _add_unknown_source_event(timeline, counterfactual):
    source_assessment = counterfactual.get("source_assessment", "")
    vector_assessment = counterfactual.get("vector_assessment", "")

    centroid_none_met = source_assessment.startswith(
        "none_of_known_candidates"
    )
    vector_none_met = vector_assessment.startswith(
        "none_of_known_candidates"
    )

    if not (centroid_none_met and vector_none_met):
        return

    events = timeline.setdefault("events", [])
    event_type = "unknown_source_review"

    # Replace an earlier event so rerunning this merge stays safe.
    events[:] = [
        event for event in events
        if event.get("type") != event_type
    ]

    events.append({
        "time": _event_time(timeline),
        "type": event_type,
        "title": "No known AIS candidate met the configured tests",
        "status": "unknown_or_untracked_source_review",
        "evidence_role": "Alternative-source hypothesis retained.",
        "details": (
            "Review dark-vessel, missing-data, and alternative-source "
            "explanations. Failure to meet these configured tests does not "
            "prove an unknown source."
        ),
    })


def merge_counterfactual_timeline(timeline, counterfactual):
    candidate = _find_candidate(timeline, counterfactual)

    _insert_or_update_release_events(
        timeline,
        candidate,
        counterfactual,
    )
    _add_candidate_summary(
        timeline,
        candidate,
        counterfactual,
    )
    _add_unknown_source_event(timeline, counterfactual)

    timeline["events"].sort(
        key=lambda event: _time_key(event.get("time"))
    )

    previous = timeline.get("interpretation", "").strip()
    if INTERPRETATION not in previous:
        timeline["interpretation"] = " ".join(
            part for part in (previous, INTERPRETATION) if part
        )

    return timeline


def main():
    if len(sys.argv) != 4:
        raise SystemExit(
            "Usage: python -m backend.forensics.merge_counterfactual_timeline "
            "<timeline.json> <counterfactual.json> <output.json>"
        )

    timeline = _read_json(sys.argv[1])
    counterfactual = _read_json(sys.argv[2])
    merged = merge_counterfactual_timeline(timeline, counterfactual)

    Path(sys.argv[3]).write_text(
        json.dumps(merged, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Merged counterfactual results into {sys.argv[3]}")


if __name__ == "__main__":
    main()