# VARUNA — Maritime Pollution Response & Forensic Attribution Suite
> **Smart India Hackathon (SIH 143)** · Automated Marine Oil Spill Identification, Lagrangian Drift Modeling & AIS Vessel Attribution Platform

VARUNA is an intelligence-grade maritime mission platform that integrates spaceborne satellite reconnaissance, hydrodynamic drift physics, contextual vessel anomaly detection, and forensic counterfactual simulation to identify and attribute offshore oil discharges to suspect vessels.

---

## System Architecture

```
                  ┌────────────────────────────────────────────────────────┐
                  │                   SENTINEL-1 C-SAR                     │
                  │   Satellite Slick Detection & Vessel Radar Contacts    │
                  └───────────────────────────┬────────────────────────────┘
                                              │
                                              ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                       BACKEND PYTHON ENGINES                                     │
├─────────────────────────┬─────────────────────────┬──────────────────────┬───────────────────────┤
│    vessels/             │    ocean/               │    forensics/        │    environment/       │
│  • surveillance.py      │  • drift.py             │  • counterfactual.py │  • impact.py          │
│  • contextual_behavior  │    (Lagrangian forward  │  • physical_consist. │  • escape_intercept   │
│  • ais_integrity.py     │     & Monte Carlo       │  • merge_timeline    │  • contextual_queue   │
│  • temporal_risk.py     │     hindcast)           │    (17-event fusion) │  • response_queue     │
└─────────────────────────┴───────────┬─────────────┴──────────────────────┴───────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                       FASTAPI REST SERVICE                                       │
│                         `api/server.py` & `api/ships_service.py` (:8000)                        │
└─────────────────────────────────────┬────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 REACT + TYPESCRIPT COMMAND UI                                    │
│                 Vite + Tailwind CSS v4 · Indian Coast Guard / Mission-Shell (:5173)              │
│    • Drift Modelling    • Satellite Recon    • Forensic Attribution    • Impact Assessment       │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

- **Python**: Version 3.10 or higher
- **Node.js**: Version 18 or higher (with `npm`)

---

## Quickstart — Running the Project

The platform runs as a decoupled architecture: a **Python FastAPI service** on port `8000` and a **Vite React interface** on port `5173`.

### 1. Start the API Backend

From the project root:

```bash
# 1. Install backend API dependencies
pip install -r api/requirements.txt

# 2. Launch the FastAPI server from the workspace root
python -m uvicorn api.server:app --reload --port 8000
```

Verify backend health by opening [http://localhost:8000/api/health](http://localhost:8000/api/health) in your browser (should return `{"status": "healthy"}`).

### 2. Start the Frontend Command Interface

Open a second terminal window:

```bash
# 1. Navigate to the frontend directory
cd frontend

# 2. Install Node dependencies (first time only)
npm install

# 3. Start the Vite development server
npm run dev
```

The frontend will be live at:
👉 **[http://localhost:5173](http://localhost:5173)**

---

## Project Structure

```
.
├── api/                             # FastAPI Service Layer
│   ├── server.py                    # REST route declarations & CORS configuration
│   ├── ships_service.py             # Scenario pipeline orchestration & multi-ship fusion
│   └── requirements.txt             # Python web dependencies (fastapi, uvicorn)
│
├── backend/                         # Core Computational Engines (Read-Only Algorithms)
│   ├── ocean/
│   │   └── drift.py                 # Forward Lagrangian drift & Monte Carlo origin hindcast
│   ├── vessels/
│   │   ├── surveillance.py          # Kinematic, speed, and route deviation analytics
│   │   ├── contextual_behavior.py   # Baseline Z-score deviations against maritime context
│   │   ├── ais_integrity.py         # Transponder blackout & spoofed jump detection
│   │   └── temporal_risk.py         # Exponential half-life temporal risk decay
│   ├── forensics/
│   │   ├── counterfactual.py        # Counterfactual backward drift simulation matrix
│   │   ├── physical_consistency.py  # 2D polygon footprint overlap & PCA orientation
│   │   └── merge_surveillance_timeline.py # 17-event forensic & surveillance timeline fusion
│   └── environment/
│       ├── impact.py                # Hydrodynamic coastal zone exposure forecast
│       ├── escape_intercept.py      # Jurisdictional boundary exit & Coast Guard intercept
│       ├── priority.py              # Multi-attribute surveillance prioritization queue
│       └── contextual_queue.py      # Context-adjusted operational queue
│
├── frontend/                        # Tactical React Command Interface
│   ├── src/
│   │   ├── App.tsx                  # Main workspace coordinator & tab router
│   │   ├── types.ts                 # Full TypeScript contract definitions
│   │   ├── api.ts                   # REST client connecting to backend
│   │   ├── index.css                # Themes (Navy / Government / Coastal) & mission-shell
│   │   └── components/
│   │       ├── Header.tsx           # Command header, IST real-time clock, theme switcher
│   │       ├── SonarMap.tsx         # Tactical radar scope with concentric range rings
│   │       ├── ThreatLedger.tsx     # Suspect vessel risk ledger & AIS integrity audit
│   │       ├── EvidenceStream.tsx   # Temporal telemetry timeline
│   │       ├── DriftTab.tsx         # Hydrodynamic forward & hindcast physics workbench
│   │       ├── SatelliteTab.tsx     # Sentinel-1 SAR correlation & intercept feasibility
│   │       ├── AttributionTab.tsx   # Counterfactual matrix, 2D vector metrics & fused timeline
│   │       ├── ImpactTab.tsx        # Dynamic dispersion timelapse scrubber & reef barriers
│   │       └── DossierTab.tsx       # Certified forensic case archive report
│   ├── package.json
│   └── vite.config.ts               # Proxies /api to http://localhost:8000
│
├── scenarios/                       # Realistic Benchmark Data & Test Scenarios
└── outputs/                         # Certified investigation outputs & dossier HTML
```

---

## Core Operational Tabs

### 1. Drift Modelling
- **Tactical Radar Scope**: Interactive sweep radar visualizing vessels, AIS transits, and backward drift clouds.
- **Threat Ledger**: Real-time suspect list with risk scores, AIS spoofing warnings, and **Commit 6 Contextual Behavioral Deviations** ($Z$-score deviations against maritime traffic baselines).
- **Forward & Backward Physics**: Simultaneous forward forecasting ($+24\text{h}$) and backward origin hindcasting ($-8\text{h}$) using ocean current and windage vectors.

### 2. Satellite Detection & Reconnaissance
- **Spaceborne SAR Correlation**: Correlates Sentinel-1 C-band synthetic aperture radar contacts with dark vessel dead-reckoning kinematics during AIS blackouts.
- **Sensor Tasking Planner**: Recommends optimal orbital reconnaissance windows ranked by hypothesis separation index.
- **Coast Guard Intercept Feasibility (Commit 7)**:
  - Detects projected Exclusive Economic Zone (EEZ) exit vectors ($+1.14\text{ h}$ at $18.999^\circ\text{N}, 73.000^\circ\text{E}$).
  - Computes fast patrol intercept rendezvous from ICGS Mumbai Base ($30\text{ kn}$).
  - Verifies tactical interception safety margin ($+10.2\text{ min}$) before the suspect enters international waters.

### 3. Vessel Attribution
- **Counterfactual Matrix**: Evaluates candidate vessels against 400 Monte Carlo Lagrangian simulations per ship.
- **Physical Consistency Vector (Commit 7)**: Multi-dimensional geometric matching incorporating:
  - Centroid Support ($99\%$)
  - 2D Polygon Boundary Support ($39\%$)
  - Footprint Area Similarity ($0.33$)
  - PCA Orientation Alignment
- **Master Surveillance Timeline (Commit 8)**: Complete 17-event chronologically fused forensic record uniting pre-spill behavioral anomalies, temporal risk decay, priority escalations, and post-spill physical matches.

### 4. Impact Assessment
- **Interactive Scrubber**: Dynamic slider and timelapse player scrubbing from $T+0\text{ h}$ to $T+24\text{ h}$.
- **Coastal Habitats**: Real-time exposure calculations for Prongs Reef Sanctuary, Mahim Estuary Biosphere, and Malabar Marine Zone.
- **Tactical Containment**: Displays automated boom deployment triggers and protective barrier statuses.

### 5. Case Archive
- Generates an official, print-ready forensic investigation dossier with full chain of custody and certified evidence ratings.

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Service health status |
| `GET` | `/api/demo/full-analysis` | Master pipeline call returning fleet analysis, drift, attribution, and intercept feasibility |
| `GET` | `/api/vessels/contextual-behavior` | Contextual baseline deviation scoring and $Z$-score signal matrix |
| `GET` | `/api/environment/escape-intercept` | Jurisdictional boundary exit projection and patrol intercept estimates |
| `POST` | `/api/vessel/analyze` | Full track behavioral anomaly inspection |
| `POST` | `/api/drift/forward` | Forward Lagrangian drift trajectory simulation |
| `POST` | `/api/drift/hindcast` | Probabilistic Monte Carlo origin hindcasting |
| `POST` | `/api/forensics/attribution` | Multi-candidate counterfactual attribution evaluation |
| `POST` | `/api/environment/impact` | Hypothetical ecological impact assessment for sensitive zones |
| `GET` | `/api/scenarios/{name}` | Loads raw scenario JSON datasets |

---

## Building for Production

To produce an optimized production build of the frontend:

```bash
cd frontend
npm run build
```

This compiles TypeScript definitions and generates production-ready static assets in `frontend/dist/`.
