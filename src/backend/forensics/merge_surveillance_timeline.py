"""Merge pre-spill surveillance context into a vessel investigation timeline."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


SURVEILLANCE_ROLE = (
    "Pre-spill surveillance context; not causal attribution evidence."
)
SCORE_MEANING = (
    "Surveillance and priority indices are configured decision-support values, "
    "not calibrated incident probabilities or guilt scores."
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


def _find_vessel(items, mmsi, label):
    matches = [item for item in items if item.get("mmsi") == mmsi]
    if matches:
        return matches[0]
    if len(items) == 1:
        return items[0]
    raise ValueError(f"Could not find {label} data for MMSI {mmsi!r}.")


def _append_once(events, event, key_fields):
    key = tuple(event.get(field) for field in key_fields)

    for index, existing in enumerate(events):
        if existing.get("type") != event.get("type"):
            continue

        existing_key = tuple(existing.get(field) for field in key_fields)
        if existing_key == key:
            events[index] = event
            return

    events.append(event)


def _merge_temporal_signals(events, mmsi, temporal_vessel):
    for signal in temporal_vessel.get("events", []):
        signal_type = signal.get("type", "surveillance_signal")
        event = {
            "time": signal.get("time"),
            "type": "temporal_risk_signal",
            "title": f"Time-decayed surveillance signal: {signal_type}",
            "signal_type": signal_type,
            "severity": signal.get("severity"),
            "configured_weight": signal.get("configured_weight"),
            "age_hours": signal.get("age_hours"),
            "decay_factor": signal.get("decay_factor"),
            "current_contribution": signal.get("current_contribution"),
            "details": signal.get("reasons", []),
            "evidence_role": SURVEILLANCE_ROLE,
        }
        _append_once(events, event, ("time", "signal_type"))


def _merge_contextual_observations(events, contextual_data, mmsi):
    if not contextual_data:
        return []

    observations = [
        observation
        for observation in contextual_data.get("observations", [])
        if observation.get("mmsi") == mmsi
    ]

    for observation in observations:
        event = {
            "time": observation.get("time"),
            "type": "contextual_behavior_signal",
            "title": "Behavior evaluated against vessel and location baseline",
            "operating_context": observation.get("operating_context"),
            "contextual_behavior_index": observation.get(
                "contextual_behavior_index"
            ),
            "reasons": observation.get("reasons", []),
            "metric_signals": observation.get("metric_signals", {}),
            "evidence_role": SURVEILLANCE_ROLE,
        }
        _append_once(events, event, ("time", "operating_context"))

    return observations


def _merge_priority_update(
    events,
    temporal_vessel,
    queue_item,
    contextual_observations,
):
    if queue_item is None:
        return

    event_time = (
        temporal_vessel.get("as_of_time")
        or queue_item.get("as_of_time")
    )
    latest_context = max(
        contextual_observations,
        key=lambda observation: _time_key(observation.get("time")),
        default={},
    )

    event = {
        "time": event_time,
        "type": "surveillance_priority_update",
        "title": "Pre-spill surveillance priority updated",
        "priority_rank": queue_item.get("priority_rank"),
        "priority_index": queue_item.get("priority_index"),
        "temporal_risk_index": queue_item.get(
            "temporal_risk_index",
            temporal_vessel.get("temporal_risk_index"),
        ),
        "incident_proxy": queue_item.get("incident_proxy"),
        "spill_opportunity": queue_item.get("spill_opportunity"),
        "potential_impact_index": queue_item.get(
            "potential_impact_index"
        ),
        "data_uncertainty": queue_item.get("data_uncertainty"),
        "contextual_behavior_index": latest_context.get(
            "contextual_behavior_index"
        ),
        "operating_context": latest_context.get("operating_context"),
        "details": (
            "Priority combines configured surveillance, spill-opportunity, "
            "impact, and uncertainty indices. It is monitoring context only."
        ),
        "score_meaning": SCORE_MEANING,
        "evidence_role": SURVEILLANCE_ROLE,
    }
    _append_once(events, event, ("time",))


def merge_surveillance_timeline(
    timeline,
    temporal_data,
    queue_data,
    contextual_data=None,
):
    mmsi = timeline.get("mmsi")
    if not mmsi:
        raise ValueError("Investigation timeline must contain an 'mmsi'")

    temporal_vessel = _find_vessel(
        temporal_data.get("vessels", []),
        mmsi,
        "temporal-risk",
    )

    queue_item = None
    queue_items = queue_data.get("queue", [])
    if queue_items:
        matches = [
            item for item in queue_items
            if item.get("mmsi") == mmsi
        ]
        if matches:
            queue_item = matches[0]
        elif len(queue_items) == 1:
            queue_item = queue_items[0]

    events = timeline.setdefault("events", [])
    _merge_temporal_signals(events, mmsi, temporal_vessel)
    contextual_observations = _merge_contextual_observations(
        events,
        contextual_data,
        mmsi,
    )
    _merge_priority_update(
        events,
        temporal_vessel,
        queue_item,
        contextual_observations,
    )

    events.sort(key=lambda event: _time_key(event.get("time")))

    previous = timeline.get("interpretation", "").strip()
    if SCORE_MEANING not in previous:
        timeline["interpretation"] = " ".join(
            part for part in (previous, SCORE_MEANING) if part
        )

    return timeline


def main():
    if len(sys.argv) not in (5, 6):
        raise SystemExit(
            "Usage: python -m backend.forensics.merge_surveillance_timeline "
            "<timeline.json> <temporal-risk.json> <priority-queue.json> "
            "[contextual-behavior.json] <output.json>"
        )

    timeline = _read_json(sys.argv[1])
    temporal_data = _read_json(sys.argv[2])
    queue_data = _read_json(sys.argv[3])

    if len(sys.argv) == 6:
        contextual_data = _read_json(sys.argv[4])
        output_path = sys.argv[5]
    else:
        contextual_data = None
        output_path = sys.argv[4]

    merged = merge_surveillance_timeline(
        timeline,
        temporal_data,
        queue_data,
        contextual_data,
    )

    Path(output_path).write_text(
        json.dumps(merged, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Merged surveillance context into {output_path}")


if __name__ == "__main__":
    main()