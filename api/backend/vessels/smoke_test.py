import argparse
import json
from pathlib import Path
from oilspill.api.backend.vessels.surveillance import analyze_track


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario_path")
    args = parser.parse_args()

    case = json.loads(
        Path(args.scenario_path).read_text(encoding="utf-8-sig")
    )
    result = analyze_track(case)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()