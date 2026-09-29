import json
import sys
from pathlib import Path


def merge_integrity_flags(timeline_data, integrity_data):
    timeline_mmsi = timeline_data.get("mmsi")
    events = list(timeline_data["events"])

    for flag in integrity_data["events"]:
        if timeline_mmsi and flag.get("mmsi") != timeline_mmsi:
            continue

        event_time = flag.get("from_time") or flag.get("start_time")
        if not event_time:
            continue

        events.append({
            "time": event_time,
            "type": "ais_integrity_flag",
            "flag_type": flag["type"],
            "title": flag["type"].replace("_", " ").title(),
            "details": flag.get("interpretation", ""),
            "related_end_time": flag.get("to_time") or flag.get("end_time"),
            "evidence_role": (
                "AIS data-quality alert; review before relying on the "
                "associated track. Not proof of spoofing or intent."
            ),
        })

    events.sort(key=lambda event: event["time"])

    return {
        **timeline_data,
        "events": events,
        "interpretation": (
            timeline_data.get("interpretation", "")
            + " AIS integrity flags are data-quality alerts for review, "
              "not proof of spoofing or intent."
        ).strip(),
    }


def main():
    if len(sys.argv) != 3:
        raise SystemExit(
            "Usage: python -m backend.forensics.merge_integrity_timeline "
            "TIMELINE.json AIS_INTEGRITY.json"
        )

    timeline_data = json.loads(
        Path(sys.argv[1]).read_text(encoding="utf-8-sig")
    )
    integrity_data = json.loads(
        Path(sys.argv[2]).read_text(encoding="utf-8-sig")
    )

    result = merge_integrity_flags(timeline_data, integrity_data)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()