import sys
from pathlib import Path
import uvicorn

CURRENT_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = CURRENT_DIR if (CURRENT_DIR / "api").exists() else CURRENT_DIR / "oilspill"

if str(WORKSPACE_DIR) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_DIR))

if __name__ == "__main__":
    print(f"Starting VARUNA API Server from {WORKSPACE_DIR} on http://127.0.0.1:8000 ...")
    uvicorn.run("api.server:app", host="127.0.0.1", port=8000, reload=True, app_dir=str(WORKSPACE_DIR))
