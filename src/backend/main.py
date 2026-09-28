"""Main entry point for running the SIH PS-143 backend simulation pipeline."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.demo_pipeline import main as run_demo_pipeline

if __name__ == "__main__":
    run_demo_pipeline()
