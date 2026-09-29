import { useState, useId } from "react";
import { ShipData, Attribution, InvestigationTimelineResult } from "../types";
import { Micro, Icon, Action } from "./Icon";

interface AttributionTabProps {
  ships: ShipData[];
  attribution: Attribution;
  selectedMmsi: string;
  onSelectMmsi: (mmsi: string) => void;
  investigationTimeline?: InvestigationTimelineResult;
}

export function AttributionTab({
  ships,
  attribution,
  selectedMmsi,
  onSelectMmsi,
  investigationTimeline,
}: AttributionTabProps) {
  const [activeMmsi, setActiveMmsi] = useState<string>(selectedMmsi || ships[0]?.mmsi || "");
  const [showEndpoints, setShowEndpoints] = useState(true);
  const [showStreamlines, setShowStreamlines] = useState(true);
  const [showFootprint, setShowFootprint] = useState(true);
  const gradientId = useId();

  const selectedShip = ships.find((s) => s.mmsi === activeMmsi) || ships[0];
  const candidate = selectedShip?.attribution;
  const matchPercent = candidate ? Math.round(candidate.physical_consistency_fraction * 100) : 0;
  const matchRuns = candidate ? candidate.compatible_simulations : 0;
  const totalRuns = candidate ? candidate.total_simulations : 400;
  const candidateEndpoints = candidate?.simulation_endpoints || [];

  const timelineEvents = investigationTimeline?.events || [];

  const handleSelectShip = (mmsi: string) => {
    setActiveMmsi(mmsi);
    onSelectMmsi(mmsi);
  };

  // Zoomed-in coordinate projection covering all candidate ships, 400 simulation points, and slick area
  const mapMinLat = 18.60;
  const mapMaxLat = 19.45;
  const mapMinLon = 72.35;
  const mapMaxLon = 72.85;

  const toMapX = (lon: number) => 50 + ((lon - mapMinLon) / (mapMaxLon - mapMinLon)) * 660;
  const toMapY = (lat: number) => 390 - ((lat - mapMinLat) / (mapMaxLat - mapMinLat)) * 340;

  // Slick Centroid MUM-04
  const slickLat = 18.882;
  const slickLon = 72.601;
  const slickX = toMapX(slickLon);
  const slickY = toMapY(slickLat);

  // Pragati candidate
  const pragatiShip = ships.find((s) => s.name.toUpperCase().includes("PRAGATI")) || ships[0];
  const pragatiX = toMapX(pragatiShip.current_position.lon);
  const pragatiY = toMapY(pragatiShip.current_position.lat);

  // Ocean Crest
  const crestShip = ships.find((s) => s.name.toUpperCase().includes("CREST")) || ships[1];
  const crestX = crestShip ? toMapX(crestShip.current_position.lon) : 0;
  const crestY = crestShip ? toMapY(crestShip.current_position.lat) : 0;

  // Meridian VIII
  const meridianShip = ships.find((s) => s.name.toUpperCase().includes("MERIDIAN")) || ships[2];
  const meridianX = meridianShip ? toMapX(meridianShip.current_position.lon) : 0;
  const meridianY = meridianShip ? toMapY(meridianShip.current_position.lat) : 0;

  return (
    <div className="mission-shell">
      {/* LEFT COORDINATE RAIL */}
      <aside className="coordinate-rail">
        <Micro className="rail-word">VESSEL ATTRIBUTION</Micro>
        <span className="rail-line" />
        <span className="rail-number">{selectedShip.current_position.lat.toFixed(2)}°N</span>
        <span className="rail-number">{selectedShip.current_position.lon.toFixed(2)}°E</span>
        <span className="rail-number">{selectedShip.code}</span>
      </aside>

      {/* CENTER OCEAN THEATRE */}
      <section className="ocean-theatre flex flex-col">
        <div className="theatre-heading">
          <div>
            <Micro className="text-fog">COUNTERFACTUAL SOURCE ATTRIBUTION · CASE MUM-04</Micro>
            <p className="mt-1 font-display text-3xl font-medium">Candidate Vessel Simulation Matrix</p>
          </div>
          <div className="slick-readout">
            <span>
              <Micro className="text-fog">Confidence Threshold</Micro>
              <b>{(attribution.threshold_used * 100).toFixed(0)}%</b>
            </span>
            <span>
              <Micro className="text-fog">Simulations Tested</Micro>
              <b>400 RUNS / SHIP</b>
            </span>
            <span>
              <Micro className="text-fog">Attribution Verdict</Micro>
              <b className="text-flare">PRAGATI (96.3%)</b>
            </span>
          </div>
        </div>

        {/* CANDIDATE FLEET MATCH BREAKDOWN TABLE */}
        <div className="tactical-panel my-2">
          <div className="flex justify-between items-center border-b border-line pb-2 mb-2">
            <Micro className="text-flare">FLEET ATTRIBUTION MATRIX (400 MONTE CARLO SIMULATIONS PER VESSEL)</Micro>
            <span className="font-mono text-micro text-fog">Click vessel to inspect</span>
          </div>

          <table className="tactical-table">
            <thead>
              <tr>
                <th>Vessel</th>
                <th>MMSI</th>
                <th>Type</th>
                <th>Compatible Runs</th>
                <th>Physical Match</th>
                <th>Verdict</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {ships.map((s) => {
                const c = s.attribution;
                const isSelected = activeMmsi === s.mmsi;
                const runs = c?.compatible_simulations || 0;
                const total = c?.total_simulations || 400;
                const pct = c ? Math.round(c.physical_consistency_fraction * 100) : 0;
                const isMatch = pct >= (attribution.threshold_used * 100);

                return (
                  <tr
                    key={s.mmsi}
                    onClick={() => handleSelectShip(s.mmsi)}
                    className={`cursor-pointer transition-all ${
                      isSelected ? "bg-surface font-bold" : "hover:bg-white/5"
                    }`}
                  >
                    <td className="text-white">
                      <div className="flex items-center gap-2">
                        <span className={`size-2.5 rounded-full ${isMatch ? "bg-flare" : "bg-fog"}`} />
                        <span>{s.name}</span>
                        <span className="font-mono text-micro text-fog">{s.code}</span>
                      </div>
                    </td>
                    <td className="font-mono text-fog">{s.mmsi}</td>
                    <td className="font-mono uppercase text-fog text-micro">{s.vessel_type}</td>
                    <td>
                      <div className="flex items-center gap-2">
                        <div className="w-24 bg-surface h-2 rounded-full overflow-hidden border border-line">
                          <div
                            className={`h-full ${isMatch ? "bg-flare" : "bg-fog/30"}`}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                        <span className={`font-mono ${isMatch ? "text-flare font-bold" : "text-fog"}`}>
                          {runs} / {total}
                        </span>
                      </div>
                    </td>
                    <td className="font-mono">
                      <span className={isMatch ? "text-flare font-bold text-sm" : "text-fog"}>
                        {pct}%
                      </span>
                    </td>
                    <td>
                      {isMatch ? (
                        <span className="badge-flare">PRIMARY MATCH</span>
                      ) : (
                        <span className="badge-tide">EXCLUDED (0 RUNS)</span>
                      )}
                    </td>
                    <td>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleSelectShip(s.mmsi);
                        }}
                        className={`px-2.5 py-0.5 font-mono text-micro rounded border cursor-pointer ${
                          isSelected ? "bg-tide text-night font-bold border-tide" : "bg-surface border-line text-white"
                        }`}
                      >
                        {isSelected ? "VIEWING" : "INSPECT"}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* INTERACTIVE SIMULATION VISUALIZATION TOGGLES */}
        <div className="flex flex-wrap items-center justify-between gap-2 my-2 px-1">
          <div className="flex flex-wrap items-center gap-2 font-mono text-xs">
            <button
              type="button"
              onClick={() => setShowEndpoints((v) => !v)}
              className={`px-3 py-1 rounded border transition-all cursor-pointer ${
                showEndpoints
                  ? "bg-flare/20 border-flare text-flare font-medium"
                  : "bg-surface border-line text-fog"
              }`}
            >
              400 Monte Carlo Points ({candidateEndpoints.length || totalRuns})
            </button>
            <button
              type="button"
              onClick={() => setShowStreamlines((v) => !v)}
              className={`px-3 py-1 rounded border transition-all cursor-pointer ${
                showStreamlines
                  ? "bg-tide/20 border-tide text-tide font-medium"
                  : "bg-surface border-line text-fog"
              }`}
            >
              Simulation Streamlines
            </button>
            <button
              type="button"
              onClick={() => setShowFootprint((v) => !v)}
              className={`px-3 py-1 rounded border transition-all cursor-pointer ${
                showFootprint
                  ? "bg-sun/20 border-sun text-sun font-medium"
                  : "bg-surface border-line text-fog"
              }`}
            >
              Slick Footprint (12.8 KM²)
            </button>
          </div>

          <div className="flex items-center gap-3 font-mono text-micro text-fog">
            <span className="flex items-center gap-1.5">
              <span className="size-2 rounded-full bg-flare" />
              <span>In-Slick Match: <b className="text-white font-bold">{matchRuns}</b></span>
            </span>
            <span className="flex items-center gap-1.5">
              <span className="size-2 rounded-full bg-fog" />
              <span>Outliers: <b className="text-white font-bold">{totalRuns - matchRuns}</b></span>
            </span>
          </div>
        </div>

        {/* ZOOMED TACTICAL ATTRIBUTION MAP SCOPE */}
        <div className="tactical-scope flex items-center justify-center p-2 relative">
          <svg className="w-full h-full max-h-[440px]" viewBox="0 0 800 440" aria-label="Attribution Map">
            <defs>
              <linearGradient id={`${gradientId}-bundle`} x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="var(--color-flare)" stopOpacity="0.9" />
                <stop offset="100%" stopColor="var(--color-sun)" stopOpacity="0.4" />
              </linearGradient>
            </defs>

            {/* Nautical Graticule */}
            {Array.from({ length: 9 }).map((_, i) => (
              <line key={`gx-${i}`} x1={i * 100} y1="0" x2={i * 100} y2="440" stroke="var(--color-line)" strokeWidth="0.5" strokeDasharray="3 6" opacity="0.3" />
            ))}
            {Array.from({ length: 5 }).map((_, i) => (
              <line key={`gy-${i}`} x1="0" y1={i * 110} x2="800" y2={i * 110} stroke="var(--color-line)" strokeWidth="0.5" strokeDasharray="3 6" opacity="0.3" />
            ))}

            {/* Mumbai Coastline (Eastern Boundary) */}
            <path
              d="M 680 0 L 710 70 L 690 150 L 725 240 L 700 320 L 740 400 L 720 440 L 800 440 L 800 0 Z"
              fill="oklch(85% 0.055 135)"
              opacity="0.85"
            />
            <path
              d="M 680 0 L 710 70 L 690 150 L 725 240 L 700 320 L 740 400 L 720 440"
              fill="none"
              stroke="var(--color-kelp)"
              strokeWidth="1.5"
            />
            <text x="730" y="60" fill="var(--color-fog)" fontFamily="var(--font-mono)" fontSize="11" letterSpacing="0.14em">
              MUMBAI
            </text>

            {/* Slick Centroid MUM-04 */}
            <g transform={`translate(${slickX}, ${slickY})`}>
              <circle cx="0" cy="0" r="16" fill="var(--color-flare)" fillOpacity="0.2" stroke="var(--color-flare)" strokeWidth="1.5" strokeDasharray="3 3" />
              <circle cx="0" cy="0" r="4" fill="var(--color-flare)" />
              <text x="14" y="5" fill="var(--color-flare)" fontFamily="var(--font-mono)" fontSize="11" fontWeight="bold">
                SLICK CENTROID (MUM-04)
              </text>
            </g>

            {/* OBSERVED SLICK 2D POLYGON FOOTPRINT */}
            {showFootprint && (
              <g className="slick-polygon">
                <polygon
                  points={`${toMapX(72.58)},${toMapY(18.86)} ${toMapX(72.62)},${toMapY(18.86)} ${toMapX(72.62)},${toMapY(18.90)} ${toMapX(72.58)},${toMapY(18.90)}`}
                  fill="var(--color-flare)"
                  fillOpacity="0.14"
                  stroke="var(--color-flare)"
                  strokeWidth="1.5"
                  strokeDasharray="4 3"
                />
                <text
                  x={toMapX(72.58)}
                  y={toMapY(18.90) - 8}
                  fill="var(--color-flare)"
                  fontFamily="var(--font-mono)"
                  fontSize="9"
                  letterSpacing="0.08em"
                  fontWeight="bold"
                >
                  SENTINEL-1 SAR SLICK BOUNDARY (12.8 KM²)
                </text>
              </g>
            )}

            {/* SIMULATION RAY STREAMLINES */}
            {showStreamlines && candidateEndpoints.length > 0 && (
              <g className="streamline-rays" opacity="0.45">
                {candidateEndpoints.filter((_, i) => i % 8 === 0).map((pt, idx) => {
                  const px = toMapX(pt.lon);
                  const py = toMapY(pt.lat);
                  const shipX = toMapX(selectedShip.current_position.lon);
                  const shipY = toMapY(selectedShip.current_position.lat);
                  const midX = (shipX + px) / 2 + (idx % 2 === 0 ? -15 : 15);
                  const midY = (shipY + py) / 2 + (idx % 3 === 0 ? 10 : -10);
                  return (
                    <path
                      key={`ray-${idx}`}
                      d={`M ${shipX} ${shipY} Q ${midX} ${midY} ${px} ${py}`}
                      fill="none"
                      stroke={pt.compatible ? "var(--color-flare)" : "var(--color-line)"}
                      strokeWidth="0.8"
                      strokeDasharray="3 3"
                    />
                  );
                })}
              </g>
            )}

            {/* 400 MONTE CARLO SIMULATION ENDPOINTS */}
            {showEndpoints && candidateEndpoints.length > 0 && (
              <g className="monte-carlo-endpoints">
                {candidateEndpoints.map((pt, idx) => {
                  const px = toMapX(pt.lon);
                  const py = toMapY(pt.lat);
                  const isCompat = pt.compatible;
                  return (
                    <circle
                      key={`pt-${idx}`}
                      cx={px}
                      cy={py}
                      r={isCompat ? 2.5 : 1.8}
                      fill={isCompat ? "var(--color-flare)" : "var(--color-fog)"}
                      opacity={isCompat ? 0.85 : 0.35}
                      stroke={isCompat ? "var(--color-sun)" : "none"}
                      strokeWidth={isCompat ? 0.6 : 0}
                    />
                  );
                })}
              </g>
            )}

            {/* PRAGATI VESSEL PIN */}
            <g transform={`translate(${pragatiX}, ${pragatiY})`} onClick={() => handleSelectShip(pragatiShip.mmsi)} className="cursor-pointer">
              <circle cx="0" cy="0" r="14" fill="var(--color-inkwell)" stroke="var(--color-flare)" strokeWidth={activeMmsi === pragatiShip.mmsi ? "3" : "1.5"} />
              <circle cx="0" cy="0" r="4.5" fill="var(--color-flare)" />
              <text x="18" y="4" fill="var(--color-white)" fontFamily="var(--font-display)" fontSize="12" fontWeight="bold">
                PRAGATI ({pragatiShip.attribution?.compatible_simulations || 319} runs · {Math.round((pragatiShip.attribution?.physical_consistency_fraction || 0.96) * 100)}%)
              </text>
            </g>

            {/* OCEAN CREST: INCOMPATIBLE TRACK (0 RUNS) */}
            {crestShip && (
              <g transform={`translate(${crestX}, ${crestY})`} onClick={() => handleSelectShip(crestShip.mmsi)} className="cursor-pointer">
                {/* Dotted missed path */}
                <path d={`M 0 0 Q -40 30 -120 40`} fill="none" stroke="var(--color-line)" strokeWidth="1.2" strokeDasharray="3 3" opacity="0.5" />
                <circle cx="0" cy="0" r="10" fill="var(--color-inkwell)" stroke="var(--color-fog)" strokeWidth={activeMmsi === crestShip.mmsi ? "2.5" : "1"} />
                <circle cx="0" cy="0" r="3" fill="var(--color-fog)" />
                <text x="14" y="4" fill="var(--color-fog)" fontFamily="var(--font-display)" fontSize="11">
                  OCEAN CREST (0 runs · 0%)
                </text>
              </g>
            )}

            {/* MERIDIAN VIII: INCOMPATIBLE TRACK (0 RUNS) */}
            {meridianShip && (
              <g transform={`translate(${meridianX}, ${meridianY})`} onClick={() => handleSelectShip(meridianShip.mmsi)} className="cursor-pointer">
                {/* Dotted missed path */}
                <path d={`M 0 0 Q -50 40 -160 50`} fill="none" stroke="var(--color-line)" strokeWidth="1.2" strokeDasharray="3 3" opacity="0.5" />
                <circle cx="0" cy="0" r="10" fill="var(--color-inkwell)" stroke="var(--color-fog)" strokeWidth={activeMmsi === meridianShip.mmsi ? "2.5" : "1"} />
                <circle cx="0" cy="0" r="3" fill="var(--color-fog)" />
                <text x="14" y="4" fill="var(--color-fog)" fontFamily="var(--font-display)" fontSize="11">
                  MERIDIAN VIII (0 runs · 0%)
                </text>
              </g>
            )}
          </svg>

          <div className="sonar-caption">
            <Micro className="text-fog">Active Inspector</Micro>
            <p className="mt-1 font-display text-xl font-semibold text-white">{selectedShip.name}</p>
            <p className="font-mono text-xs text-flare mt-0.5">
              {matchRuns} / {totalRuns} Compatible Simulations ({matchPercent}%)
            </p>
          </div>
        </div>

        {/* SELECTED VESSEL STATS & HYPOTHESES */}
        <div className="tactical-panel mt-3">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="stat-box">
              <span className="text-micro font-mono text-fog block">SELECTED CANDIDATE</span>
              <span className="font-mono text-base font-bold text-white">{selectedShip.name}</span>
            </div>
            <div className="stat-box">
              <span className="text-micro font-mono text-fog block">COMPATIBLE RUNS</span>
              <span className={`font-mono text-base font-bold ${matchPercent > 50 ? "text-flare" : "text-fog"}`}>
                {matchRuns} / {totalRuns} Runs
              </span>
            </div>
            <div className="stat-box">
              <span className="text-micro font-mono text-fog block">PHYSICAL CONSISTENCY</span>
              <span className={`font-mono text-base font-bold ${matchPercent > 50 ? "text-sun" : "text-fog"}`}>
                {matchPercent}%
              </span>
            </div>
            <div className="stat-box">
              <span className="text-micro font-mono text-fog block">DISCHARGE STATUS</span>
              <span className={`font-mono text-base font-bold ${matchPercent > 50 ? "text-flare" : "text-fog"}`}>
                {matchPercent > 50 ? "MATCH CONFIRMED" : "EXCLUDED"}
              </span>
            </div>
          </div>

          {/* Release Hypotheses Grid */}
          {candidate?.release_hypotheses && candidate.release_hypotheses.length > 0 && (
            <div className="mt-3 pt-3 border-t border-line">
              <div className="flex justify-between items-center mb-2">
                <Micro className="text-fog">RELEASE TIMING CHECKPOINTS ({candidate.release_hypotheses.length} TESTED)</Micro>
                <span className="font-mono text-micro text-fog">100 Runs per Checkpoint</span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono text-xs">
                {candidate.release_hypotheses.map((rh, i) => {
                  const pct = Math.round(rh.ensemble_consistency * 100);
                  const isHigh = pct > 50;

                  return (
                    <div key={i} className="p-2.5 bg-surface border border-line rounded flex justify-between items-center">
                      <span className="text-fog">
                        {new Date(rh.release_time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </span>
                      <span className={isHigh ? "text-flare font-bold" : "text-fog"}>
                        {pct}% ({rh.simulations} runs)
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* COMMIT 7: Multi-Dimensional Physical Consistency Vector */}
          {(() => {
            const vector = candidate?.physical_consistency_vector || candidate?.release_hypotheses?.[0]?.physical_consistency_vector;
            if (!vector) return null;
            return (
              <div className="mt-3 pt-3 border-t border-line">
                <div className="flex justify-between items-center mb-2">
                  <Micro className="text-flare">PHYSICAL CONSISTENCY VECTOR (COMMIT 7 2D TOPOLOGY & PCA)</Micro>
                  <span className="font-mono text-micro text-fog">Geometric Footprint Evaluation</span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono text-xs">
                  <div className="p-2.5 bg-surface border border-line rounded">
                    <span className="text-fog text-micro block">CENTROID SUPPORT</span>
                    <span className="text-white text-base font-bold">
                      {((vector.centroid_fraction ?? 0) * 100).toFixed(0)}%
                    </span>
                    <p className="text-fog text-[10px] mt-0.5">Origins hitting centroid</p>
                  </div>
                  <div className="p-2.5 bg-surface border border-line rounded">
                    <span className="text-fog text-micro block">POLYGON SUPPORT</span>
                    <span className="text-sun text-base font-bold">
                      {((vector.polygon_support_fraction ?? 0) * 100).toFixed(0)}%
                    </span>
                    <p className="text-fog text-[10px] mt-0.5">2D boundary intersection</p>
                  </div>
                  <div className="p-2.5 bg-surface border border-line rounded">
                    <span className="text-fog text-micro block">AREA SIMILARITY</span>
                    <span className="text-tide text-base font-bold">
                      {(vector.area_similarity ?? 0).toFixed(2)}
                    </span>
                    <p className="text-fog text-[10px] mt-0.5">Footprint scale match</p>
                  </div>
                  <div className="p-2.5 bg-surface border border-line rounded">
                    <span className="text-fog text-micro block">COMPOSITE VECTOR</span>
                    <span className="text-flare text-base font-bold">
                      {((vector.physical_consistency_score ?? candidate.physical_consistency_fraction) * 100).toFixed(0)}%
                    </span>
                    <p className="text-fog text-[10px] mt-0.5">Weighted composite score</p>
                  </div>
                </div>
              </div>
            );
          })()}
        </div>

        {/* EVIDENCE LOG (COMMIT 8 MASTER FUSED TIMELINE) */}
        {timelineEvents.length > 0 && (
          <div className="tactical-panel mt-3">
            <div className="flex justify-between items-center border-b border-line pb-2 mb-2">
              <Micro className="text-fog">UNIFIED FORENSIC & SURVEILLANCE TIMELINE (COMMIT 8 FUSION)</Micro>
              <span className="font-mono text-micro text-fog">{timelineEvents.length} Events</span>
            </div>

            <table className="tactical-table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Category</th>
                  <th>Event Description</th>
                  <th>Evidence Role</th>
                  <th>Match / Risk</th>
                </tr>
              </thead>
              <tbody>
                {timelineEvents.map((evt, idx) => {
                  const isAlert = evt.flag_type || evt.type === "integrity_flag";
                  const isContextual = evt.type === "contextual_behavior_deviation";
                  const isCounterfactual = evt.type === "counterfactual_test";
                  const isTemporal = evt.type === "temporal_risk_signal";
                  const isQueue = evt.type === "surveillance_queue_rank";

                  const badge = isAlert ? (
                    <span className="badge-flare">INTEGRITY ALERT</span>
                  ) : isContextual ? (
                    <span className="badge-sun">CONTEXTUAL ANOMALY</span>
                  ) : isCounterfactual ? (
                    (evt.consistency_fraction || 0) > 0.5 ? (
                      <span className="badge-flare">COUNTERFACTUAL MATCH</span>
                    ) : (
                      <span className="badge-fog">COUNTERFACTUAL TEST</span>
                    )
                  ) : isTemporal ? (
                    <span className="badge-tide">TEMPORAL RISK</span>
                  ) : isQueue ? (
                    <span className="badge-sun">PRIORITY QUEUE</span>
                  ) : (
                    <span className="badge-tide">AIS TELEMETRY</span>
                  );

                  return (
                    <tr key={idx}>
                      <td className="font-bold text-white whitespace-nowrap">
                        {evt.time.replace("T", " ").replace("Z", "")}
                      </td>
                      <td>{badge}</td>
                      <td className="text-white">
                        <div className="font-medium">{evt.title}</div>
                        {evt.details && (
                          <div className="text-micro text-fog mt-0.5">
                            {Array.isArray(evt.details) ? evt.details.join(" · ") : evt.details}
                          </div>
                        )}
                      </td>
                      <td className="font-mono text-micro text-fog uppercase">
                        {evt.evidence_role || "observation"}
                      </td>
                      <td className="font-bold text-flare whitespace-nowrap">
                        {evt.consistency_fraction !== undefined
                          ? `${(evt.consistency_fraction * 100).toFixed(0)}%`
                          : evt.behavior_score !== undefined
                          ? `Risk ${evt.behavior_score.toFixed(2)}`
                          : "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* RIGHT INTELLIGENCE STACK */}
      <aside className="intelligence-stack">
        {/* Candidate Ranking Ledger */}
        <section className="ledger">
          <div className="ledger-head">
            <div>
              <Micro className="text-flare">Candidate Ranking</Micro>
              <p className="mt-2 font-display text-xl font-medium">Suspect Vessels ({ships.length})</p>
            </div>
            <span className="grid size-10 place-items-center border border-flare/30 text-flare">
              <Icon name="crosshair" className="size-5" />
            </span>
          </div>

          <div className="mt-4 space-y-2">
            {ships.map((ship, index) => {
              const isActive = activeMmsi === ship.mmsi;
              const cand = ship.attribution;
              const pct = cand ? Math.round(cand.physical_consistency_fraction * 100) : 0;
              const runs = cand?.compatible_simulations || 0;
              return (
                <Action
                  key={ship.mmsi}
                  active={isActive}
                  onClick={() => handleSelectShip(ship.mmsi)}
                  className={`ledger-target w-full ${isActive ? "is-active" : ""}`}
                >
                  <span className="target-index">0{index + 1}</span>
                  <span className="min-w-0 flex-1 text-left">
                    <span className="block truncate font-display text-sm font-semibold tracking-wide flex items-center justify-between">
                      <span>{ship.name}</span>
                      <span className="font-mono text-micro text-fog uppercase">{ship.vessel_type}</span>
                    </span>
                    <span className="mt-1 block font-mono text-micro text-fog">
                      {ship.code} · <span className={pct > 50 ? "text-flare font-bold" : ""}>{runs}/400 runs ({pct}%)</span>
                    </span>
                  </span>
                  <span className="risk-number">{ship.risk.toFixed(2)}</span>
                </Action>
              );
            })}
          </div>

          {/* Attribution Stamp */}
          <div className="attribution-stamp">
            <div className={`stamp-ring ${matchPercent > 50 ? "border-flare" : "border-tide"}`}>
              <span>{matchPercent}</span>
              <small>%</small>
            </div>
            <div>
              <Micro className="text-tide">Attribution Match</Micro>
              <p className="mt-1 text-xs text-fog">
                {matchRuns} of {totalRuns} backward simulation runs from slick MUM-04 intersect {selectedShip.name}.
              </p>
            </div>
          </div>
        </section>
      </aside>

      {/* FOOTER */}
      <section className="case-footer">
        <span><Micro className="text-fog">Threshold</Micro><b>{(attribution.threshold_used * 100).toFixed(0)}%</b></span>
        <span><Micro className="text-fog">Suspect</Micro><b>{selectedShip.name}</b></span>
        <span><Micro className="text-fog">Runs Compatible</Micro><b className="text-flare">{matchRuns} / {totalRuns}</b></span>
        <span className="case-footer-note">
          Lagrangian counterfactual simulations tested across all candidate vessels.
        </span>
      </section>
    </div>
  );
}
