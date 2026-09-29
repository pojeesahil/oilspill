import { useState, useEffect } from "react";
import { Header } from "./components/Header";
import { SonarMap } from "./components/SonarMap";
import { ThreatLedger } from "./components/ThreatLedger";
import { EvidenceStream } from "./components/EvidenceStream";
import { AttributionTab } from "./components/AttributionTab";
import { ImpactTab } from "./components/ImpactTab";
import { SatelliteTab } from "./components/SatelliteTab";
import { DossierTab } from "./components/DossierTab";
import { DriftTab } from "./components/DriftTab";
import { fetchFullAnalysis, refreshAnalysis } from "./api";
import { FullAnalysisResponse } from "./types";
import { Micro, Icon } from "./components/Icon";

const TABS = [
  "Drift modelling",
  "Satellite detection",
  "Vessel attribution",
  "Impact assessment",
  "Case archive",
];

export default function App() {
  const [theme, setTheme] = useState<"government" | "navy" | "coastal">("government");
  const [data, setData] = useState<FullAnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [activeTab, setActiveTab] = useState("Drift modelling");
  const [driftViewMode, setDriftViewMode] = useState<"radar" | "physics">("radar");

  const [selectedMmsi, setSelectedMmsi] = useState<string>("IND-7319");

  useEffect(() => {
    fetchFullAnalysis()
      .then((res) => {
        setData(res);
        if (res.ships && res.ships.length > 0) {
          setSelectedMmsi(res.ships[0].mmsi);
        } else if (res.surveillance_queue?.length > 0) {
          setSelectedMmsi(res.surveillance_queue[0].mmsi);
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      const res = await refreshAnalysis();
      setData(res);
    } catch (e: any) {
      console.error(e);
    } finally {
      setRefreshing(false);
    }
  };

  if (loading) {
    return (
      <div className={`theme-${theme} min-h-screen bg-night text-white flex items-center justify-center`}>
        <Micro className="text-tide">Connecting to VARUNA Maritime Multi-Ship Intelligence Engine...</Micro>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className={`theme-${theme} min-h-screen bg-night text-white flex items-center justify-center`}>
        <Micro className="text-flare">Error loading multi-ship telemetry: {error}</Micro>
      </div>
    );
  }

  const ships = data.ships && data.ships.length > 0 ? data.ships : [];
  const selectedShip = ships.find((s) => s.mmsi === selectedMmsi) || ships[0];
  const activeCase = data.active_case || {
    case_id: "MUM-04",
    label: "MUM-04 · Western Offshore",
    slick_area_km2: 12.8,
    est_age: "03H 36M",
    orientation: "NE 042°",
  };

  const primaryImpactZone = selectedShip?.impact?.zones?.[0];

  return (
    <main className={`theme-${theme} min-h-screen overflow-x-hidden bg-night text-white`}>
      <div className="noise pointer-events-none fixed inset-0 z-50" />
      <Header theme={theme} onThemeChange={setTheme} />

      <nav className="future-nav flex items-center justify-between" aria-label="Future application modules">
        <div className="flex items-center gap-2 overflow-x-auto">
          <span className="future-nav-label">Workspace</span>
          {TABS.map((item) => (
            <span
              key={item}
              className={activeTab === item ? "future-nav-item current" : "future-nav-item"}
              onClick={() => setActiveTab(item)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => e.key === "Enter" && setActiveTab(item)}
            >
              {item}
            </span>
          ))}
        </div>

        <div className="flex items-center gap-3 pr-4 font-mono text-xs">
          {activeTab === "Drift modelling" && (
            <div className="flex items-center rounded border border-line bg-surface/50 p-0.5">
              <button
                type="button"
                onClick={() => setDriftViewMode("radar")}
                className={`px-2.5 py-0.5 rounded cursor-pointer transition-all ${
                  driftViewMode === "radar" ? "bg-flare text-night font-bold" : "text-fog hover:text-white"
                }`}
              >
                RADAR
              </button>
              <button
                type="button"
                onClick={() => setDriftViewMode("physics")}
                className={`px-2.5 py-0.5 rounded cursor-pointer transition-all ${
                  driftViewMode === "physics" ? "bg-tide text-night font-bold" : "text-fog hover:text-white"
                }`}
              >
                WORKBENCH (+BAYESIAN)
              </button>
            </div>
          )}

          <button
            type="button"
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center gap-1.5 px-3 py-1 rounded border border-line bg-surface hover:border-flare text-xs font-mono text-fog hover:text-white transition-all cursor-pointer"
          >
            <span className={`size-2 rounded-full ${refreshing ? "bg-sun animate-ping" : "bg-kelp"}`} />
            <span>{refreshing ? "SIMULATING..." : "RECOMPUTE"}</span>
          </button>
        </div>
      </nav>

      {activeTab === "Drift modelling" && driftViewMode === "radar" && (
        <div className="mission-shell">
          <aside className="coordinate-rail">
            <Micro className="rail-word">DRIFT & HYDRODYNAMICS</Micro>
            <span className="rail-line" />
            <span className="rail-number">{selectedShip?.current_position.lat.toFixed(2) || "19°07"}</span>
            <span className="rail-number">{selectedShip?.current_position.lon.toFixed(2) || "72°87"}</span>
            <span className="rail-number">{selectedShip?.code || "M-07"}</span>
          </aside>

          <section className="ocean-theatre flex flex-col">
            <div className="theatre-heading">
              <div>
                <Micro className="text-fog">{activeCase.label}</Micro>
                <p className="mt-1 font-display text-3xl font-medium">Tactical Sonar & Hydrodynamic Drift</p>
                <p className="font-mono text-xs text-tide mt-0.5">
                  Tracking {ships.length} ships with individual forecast & backtrack physics
                </p>
              </div>
              <div className="slick-readout">
                <span>
                  <Micro className="text-fog">Slick area</Micro>
                  <b>{activeCase.slick_area_km2} KM²</b>
                </span>
                <span>
                  <Micro className="text-fog">Est. age</Micro>
                  <b>{activeCase.est_age}</b>
                </span>
                <span>
                  <Micro className="text-fog">Orientation</Micro>
                  <b>{activeCase.orientation}</b>
                </span>
              </div>
            </div>

            <div className="flex-1 min-h-[460px] flex items-center justify-center">
              <SonarMap
                ships={ships}
                selectedMmsi={selectedMmsi}
                onSelectMmsi={setSelectedMmsi}
              />
            </div>

            {selectedShip && <EvidenceStream ship={selectedShip} />}
          </section>

          <aside className="intelligence-stack">
            <ThreatLedger
              ships={ships}
              selectedMmsi={selectedMmsi}
              onSelectMmsi={setSelectedMmsi}
              temporalRisk={data.temporal_risk}
              contextualBehavior={data.contextual_behavior}
            />

            <section className="eco-card">
              <div className="eco-icon">
                <Icon name="shield" className="size-6" />
              </div>
              <div className="min-w-0 flex-1">
                <Micro className="text-sun">Ecological intercept · {selectedShip?.name}</Micro>
                <p className="mt-1 truncate font-display text-base font-semibold">
                  {primaryImpactZone?.name || "Coastal Reserve"}
                </p>
                <p className="mt-1 text-xs text-fog">
                  Exposure probability:{" "}
                  <b className="text-white">
                    {((primaryImpactZone?.exposure_fraction || 0) * 100).toFixed(0)}%
                  </b>
                </p>
              </div>
              <span className="font-mono text-lg text-sun">
                {primaryImpactZone?.earliest_eta_hours
                  ? `+${primaryImpactZone.earliest_eta_hours.toFixed(1)}h`
                  : "N/A"}
              </span>
            </section>
          </aside>

          <section className="case-footer">
            <span>
              <Micro className="text-fog">Detected</Micro>
              <b>18 JUN · 22:48 IST</b>
            </span>
            <span>
              <Micro className="text-fog">Satellite Scene</Micro>
              <b>S1A-IW-GRD</b>
            </span>
            <span>
              <Micro className="text-fog">Review status</Micro>
              <b>OPEN CASE</b>
            </span>
            <span className="case-footer-note">
              AUTOMATED PIPELINE: AIS Anomaly Engine → Forward Drift Forecast (+24h) → Backward Hindcast (-8h) → Counterfactual Attribution | FLEET: {ships.length} VESSELS
            </span>
          </section>
        </div>
      )}

      {activeTab === "Drift modelling" && driftViewMode === "physics" && (
        <DriftTab
          ships={ships}
          selectedMmsi={selectedMmsi}
          onSelectMmsi={setSelectedMmsi}
          forecastUpdate={data.forecast_update}
        />
      )}

      {activeTab === "Vessel attribution" && (
        <AttributionTab
          ships={ships}
          attribution={data.overall_attribution || data.attribution}
          selectedMmsi={selectedMmsi}
          onSelectMmsi={setSelectedMmsi}
          investigationTimeline={data.investigation_timeline}
        />
      )}

      {activeTab === "Impact assessment" && (
        <ImpactTab
          ships={ships}
          selectedMmsi={selectedMmsi}
          onSelectMmsi={setSelectedMmsi}
          overallResponseQueue={data.overall_response_queue}
        />
      )}

      {activeTab === "Satellite detection" && (
        <SatelliteTab
          ships={ships}
          selectedMmsi={selectedMmsi}
          onSelectMmsi={setSelectedMmsi}
          deadReckoning={data.dead_reckoning}
          observationPlan={data.observation_plan}
          escapeIntercept={data.escape_intercept}
          aisTrust={data.ais_trust}
        />
      )}

      {activeTab === "Case archive" && (
        <DossierTab data={data} />
      )}
    </main>
  );
}
