import html
import json
import sys
from pathlib import Path


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def esc(value):
    return html.escape(str(value))


def make_dossier(evidence, timeline, queue_data, response):
    mmsi = timeline.get("mmsi", "Unspecified vessel")

    hypotheses = []
    for hypothesis in evidence.get("hypotheses", []):
        items = "".join(
            f"<li>{esc(item.get('message', item.get('direction', '')))}</li>"
            for item in hypothesis.get("evidence", [])
        )
        hypotheses.append(
            "<article class='panel'>"
            f"<h3>{esc(hypothesis.get('hypothesis', 'Hypothesis'))}</h3>"
            f"<p class='status'>{esc(hypothesis.get('status', ''))}</p>"
            f"<ul>{items}</ul></article>"
        )

    ranked = []
    for vessel in queue_data.get("queue", []):
        ranked.append(
            "<tr>"
            f"<td>{esc(vessel.get('priority_rank', ''))}</td>"
            f"<td>{esc(vessel.get('mmsi', ''))}</td>"
            f"<td>{esc(vessel.get('temporal_risk_index', ''))}</td>"
            f"<td>{esc(vessel.get('spill_opportunity', ''))}</td>"
            f"<td>{esc(vessel.get('potential_impact_index', ''))}</td>"
            f"<td>{esc(vessel.get('priority_index', ''))}</td>"
            "</tr>"
        )

    actions = []
    for item in response.get("response_queue", []):
        recommendations = "".join(
            f"<li>{esc(action)}</li>"
            for action in item.get("recommended_actions", [])
        )
        actions.append(
            "<article class='panel'>"
            f"<h3>{esc(item.get('zone', 'Zone'))} "
            f"· Priority {esc(item.get('priority_rank', ''))}</h3>"
            f"<p>Exposure: {esc(item.get('exposure_fraction', ''))} "
            f"| Earliest ETA: {esc(item.get('earliest_eta_hours', ''))} h</p>"
            f"<ul>{recommendations}</ul></article>"
        )

    events = []
    for event in timeline.get("events", []):
        details = event.get("details", "")
        if isinstance(details, list):
            details = ", ".join(map(str, details))
        events.append(
            "<tr>"
            f"<td>{esc(event.get('time', ''))}</td>"
            f"<td>{esc(event.get('title', event.get('type', '')))}</td>"
            f"<td>{esc(details)}</td>"
            f"<td>{esc(event.get('evidence_role', ''))}</td>"
            "</tr>"
        )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Investigation dossier — {esc(mmsi)}</title>
<style>
body {{ margin: 0; background: #f3f6f8; color: #172b3a;
       font: 15px/1.5 Segoe UI, Arial, sans-serif; }}
main {{ max-width: 1100px; margin: 32px auto; padding: 0 22px; }}
header {{ background: #123047; color: white; padding: 28px;
          border-radius: 12px; }}
h1 {{ margin: 0 0 6px; font-size: 28px; }}
h2 {{ margin-top: 30px; color: #123047; }}
h3 {{ margin: 0 0 8px; }}
.panel {{ background: white; border: 1px solid #d8e1e7;
          border-radius: 10px; padding: 16px 20px; margin: 12px 0; }}
.status {{ color: #176b61; font-weight: 600; }}
.notice {{ border-left: 4px solid #d49a32; padding: 10px 14px;
           background: #fff8e8; }}
table {{ width: 100%; border-collapse: collapse; background: white; }}
th, td {{ text-align: left; padding: 10px; border: 1px solid #d8e1e7;
          vertical-align: top; }}
th {{ background: #e8eef2; }}
.small {{ color: #526775; font-size: 13px; }}
@media print {{
  body {{ background: white; }}
  main {{ max-width: none; margin: 0; padding: 0; }}
  header {{ print-color-adjust: exact; -webkit-print-color-adjust: exact; }}
  .panel, table {{ break-inside: avoid; }}
}}
</style>
</head>
<body><main>
<header>
  <h1>Oil Spill Investigation Dossier</h1>
  <div>Vessel: {esc(mmsi)}</div>
  <div class="small">Operational forensic analysis assembled from multi-sensor intelligence</div>
</header>
<p class="notice"><strong>Interpretation:</strong>
This dossier contains forensic hydrodynamic hindcast results and AIS kinematic verification. Scores are physical consistency indices under the specified atmospheric and oceanographic forcing. AIS integrity alerts highlight telemetry anomalies for naval and coast guard operational assessment.</p>
<h2>Candidate evidence</h2>
{''.join(hypotheses) or '<p>No candidate hypotheses supplied.</p>'}
<h2>Surveillance priority</h2>
<table><thead><tr><th>Rank</th><th>Vessel</th><th>Temporal index</th>
<th>Spill opportunity</th><th>Potential impact</th><th>Priority index</th>
</tr></thead><tbody>{''.join(ranked)}</tbody></table>
<h2>Recommended response</h2>
{''.join(actions) or '<p>No response recommendations supplied.</p>'}
<h2>Investigation timeline</h2>
<table><thead><tr><th>Time</th><th>Event</th><th>Details</th><th>Evidence role</th>
</tr></thead><tbody>{''.join(events)}</tbody></table>
</main></body></html>"""


def main():
    if len(sys.argv) != 6:
        raise SystemExit(
            "Usage: python -m backend.forensics.dossier "
            "EVIDENCE.json TIMELINE.json QUEUE.json RESPONSE.json OUTPUT.html"
        )

    evidence, timeline, queue_data, response = map(load_json, sys.argv[1:5])
    report = make_dossier(evidence, timeline, queue_data, response)
    Path(sys.argv[5]).write_text(report, encoding="utf-8")
    print(f"Wrote dossier: {sys.argv[5]}")


if __name__ == "__main__":
    main()