import { useState, useId } from "react";
import { ShipData, ForecastUpdateResult } from "../types";
import { Micro, Icon, Action } from "./Icon";

interface DriftTabProps {
  ships: ShipData[];
  selectedMmsi: string;
  onSelectMmsi: (mmsi: string) => void;
  forecastUpdate?: ForecastUpdateResult;
}

export function DriftTab({ ships, selectedMmsi, onSelectMmsi, forecastUpdate }: DriftTabProps) {
  const [activeMmsi, setActiveMmsi] = useState<string>(selectedMmsi || ships[0]?.mmsi || "");
  const [showForward, setShowForward] = useState(true);
  const [showBacktrack, setShowBacktrack] = useState(true);
  const [showOrigins, setShowOrigins] = useState(true);
  const gradientId = useId();

  const currentShip = ships.find((s) => s.mmsi === activeMmsi) || ships[0];
  const { drift_forecast, drift_backtrack } = currentShip;
  const { forward_track } = drift_forecast;
  const { backtrack_track, hindcast } = drift_backtrack;

  const handleSelectShip = (mmsi: string) => {
    setActiveMmsi(mmsi);
    onSelectMmsi(mmsi);
  };

  // Dynamically compute zoom bounding box around active ship + its trajectories + slick
  const allLats = [
    currentShip.current_position.lat,
    18.882, // slick
    ...forward_track.map((p) => p.lat),
    ...backtrack_track.map((p) => p.lat),
  ];
  const allLons = [
    currentShip.current_position.lon,
    72.601, // slick
    ...forward_track.map((p) => p.lon),
    ...backtrack_track.map((p) => p.lon),
  ];

  const minLat = Math.min(...allLats);
  const maxLat = Math.max(...allLats);
  const minLon = Math.min(...allLons);
  const maxLon = Math.max(...allLons);

  const padLat = Math.max(0.03, (maxLat - minLat) * 0.18);
  const padLon = Math.max(0.04, (maxLon - minLon) * 0.18);

  const bMinLat = minLat - padLat;
  const bMaxLat = maxLat + padLat;
  const bMinLon = minLon - padLon;
  const bMaxLon = maxLon + padLon;

  const toMapX = (lon: number) => 60 + ((lon - bMinLon) / (bMaxLon - bMinLon)) * 680;
  const toMapY = (lat: number) => 380 - ((lat - bMinLat) / (bMaxLat - bMinLat)) * 320;

  // Convert points to SVG path on the 800x440 canvas
  const pointsToPath = (pts: { lat: number; lon: number }[]) => {
    if (!pts || pts.length === 0) return "";
    const coords = pts.map((p) => [toMapX(p.lon), toMapY(p.lat)]);
    let d = `M ${coords[0][0]} ${coords[0][1]}`;
    for (let i = 1; i < coords.length; i++) {
      d += ` L ${coords[i][0]} ${coords[i][1]}`;
    }
    return d;
  };

  const forwardPath = pointsToPath(forward_track);
  const backtrackPath = pointsToPath(backtrack_track);
  const correctedPath = forecastUpdate ? pointsToPath(forecastUpdate.corrected_forecast) : "";

  const isPrimarySuspect = currentShip.mmsi === "IND-7319";
  const backtrackEnd = backtrack_track[backtrack_track.length - 1];
  
  // For primary suspect PRAGATI, align slick MUM-04 directly on its backtrack release origin
  const slickCoords = isPrimarySuspect && backtrackEnd
    ? { lat: backtrackEnd.lat, lon: backtrackEnd.lon }
    : { lat: 18.882, lon: 72.601 };

  const shipX = toMapX(currentShip.current_position.lon);
  const shipY = toMapY(currentShip.current_position.lat);

  const slickX = toMapX(slickCoords.lon);
  const slickY = toMapY(slickCoords.lat);

  const forwardEnd = forward_track[forward_track.length - 1];
  const [fwdEndX, fwdEndY] = forwardEnd
    ? [toMapX(forwardEnd.lon), toMapY(forwardEnd.lat)]
    : [0, 0];

  const [bwdEndX, bwdEndY] = backtrackEnd
    ? [toMapX(backtrackEnd.lon), toMapY(backtrackEnd.lat)]
    : [0, 0];

  const originPoints = hindcast.origins.map((o) => ({
    x: toMapX(o.lon),
    y: toMapY(o.lat),
  }));

  return (
    <div className="mission-shell">
      {/* LEFT COORDINATE RAIL */}
      <aside className="coordinate-rail">
        <Micro className="rail-word">DRIFT MODELLING</Micro>
        <span className="rail-line" />
        <span className="rail-number">{currentShip.current_position.lat.toFixed(2)}°N</span>
        <span className="rail-number">{currentShip.current_position.lon.toFixed(2)}°E</span>
        <span className="rail-number">{currentShip.code}</span>
      </aside>

      {/* CENTER OCEAN THEATRE */}
      <section className="ocean-theatre flex flex-col">
        <div className="theatre-heading">
          <div>
            <Micro className="text-fog">DRIFT & DISPERSION · {currentShip.name}</Micro>
            <p className="mt-1 font-display text-3xl font-medium">Trajectory Simulation</p>
          </div>
          <div className="slick-readout">
            <span>
              <Micro className="text-fog">Forecast Horizon</Micro>
              <b>+{drift_forecast.duration_hours}H</b>
            </span>
            <span>
              <Micro className="text-fog">Backtrack Window</Micro>
              <b>-{drift_backtrack.duration_hours}H</b>
            </span>
            <span>
              <Micro className="text-fog">Ensemble Size</Micro>
              <b>{hindcast.run_count} RUNS</b>
            </span>
          </div>
        </div>

        {/* CONTROLS */}
        <div className="flex items-center justify-between gap-2 my-2 px-1">
          <div className="flex gap-2 text-xs font-mono">
            <button
              type="button"
              onClick={() => setShowForward((v) => !v)}
              className={`px-3 py-1 rounded border transition-all cursor-pointer ${
                showForward
                  ? "bg-flare/20 border-flare text-flare font-medium"
                  : "bg-surface border-line text-fog"
              }`}
            >
              Forecast (+24h)
            </button>
            <button
              type="button"
              onClick={() => setShowBacktrack((v) => !v)}
              className={`px-3 py-1 rounded border transition-all cursor-pointer ${
                showBacktrack
                  ? "bg-tide/20 border-tide text-tide font-medium"
                  : "bg-surface border-line text-fog"
              }`}
            >
              Backtrack (-8h)
            </button>
            <button
              type="button"
              onClick={() => setShowOrigins((v) => !v)}
              className={`px-3 py-1 rounded border transition-all cursor-pointer ${
                showOrigins
                  ? "bg-sun/20 border-sun text-sun font-medium"
                  : "bg-surface border-line text-fog"
              }`}
            >
              Origin Cloud ({hindcast.run_count})
            </button>
          </div>

          <div className="flex gap-4 font-mono text-micro text-fog">
            <span>Current: <b className="text-white">0.15 kn E</b></span>
            <span>Wind: <b className="text-white">2.0 kn W</b></span>
          </div>
        </div>

        {/* CLEAN MARITIME BASIN MAP */}
        <div className="tactical-scope flex items-center justify-center p-2 relative">
          <svg className="w-full h-full max-h-[440px]" viewBox="0 0 800 440" aria-label="Drift Map">
            <defs>
              <linearGradient id={`${gradientId}-fwd`} x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="var(--color-flare)" stopOpacity="1" />
                <stop offset="100%" stopColor="var(--color-sun)" stopOpacity="0.6" />
              </linearGradient>
              <linearGradient id={`${gradientId}-bwd`} x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="var(--color-tide)" stopOpacity="1" />
                <stop offset="100%" stopColor="var(--color-fog)" stopOpacity="0.4" />
              </linearGradient>
            </defs>

            {/* Subtle Nautical Grid */}
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

            {/* Slick Centroid / Backtrack Release Origin */}
            <g transform={`translate(${slickX}, ${slickY})`}>
              <circle cx="0" cy="0" r="16" fill="var(--color-flare)" fillOpacity="0.2" stroke="var(--color-flare)" strokeWidth="1.5" strokeDasharray="3 3" />
              <circle cx="0" cy="0" r="4.5" fill="var(--color-flare)" />
              <text x="14" y="-3" fill="var(--color-flare)" fontFamily="var(--font-mono)" fontSize="11" fontWeight="bold">
                SLICK MUM-04 {isPrimarySuspect ? "· DISCHARGE ORIGIN" : ""}
              </text>
              <text x="14" y="11" fill="var(--color-fog)" fontFamily="var(--font-mono)" fontSize="9">
                {slickCoords.lat.toFixed(3)}°N, {slickCoords.lon.toFixed(3)}°E {isPrimarySuspect ? "(-8h Backtrack Intersect)" : "(Observed Centroid)"}
              </text>
            </g>

            {/* Monte Carlo Origin Dispersion Particles */}
            {showOrigins && (
              <g className="origin-dots">
                {originPoints.map((pt, i) => (
                  <circle key={i} cx={pt.x} cy={pt.y} r="2" fill="var(--color-sun)" opacity="0.35" />
                ))}
              </g>
            )}

            {/* Backtrack Path */}
            {showBacktrack && backtrackPath && (
              <g>
                <path
                  d={backtrackPath}
                  fill="none"
                  stroke={`url(#${gradientId}-bwd)`}
                  strokeWidth="2.5"
                  strokeDasharray="4 4"
                  strokeLinecap="round"
                />
                {!isPrimarySuspect && (
                  <>
                    <circle cx={bwdEndX} cy={bwdEndY} r="4" fill="var(--color-tide)" />
                    <text x={bwdEndX + 8} y={bwdEndY + 4} fill="var(--color-tide)" fontFamily="var(--font-mono)" fontSize="10">
                      -8h
                    </text>
                  </>
                )}
              </g>
            )}

            {/* Forward Forecast Path */}
            {showForward && forwardPath && (
              <g>
                <path
                  d={forwardPath}
                  fill="none"
                  stroke={`url(#${gradientId}-fwd)`}
                  strokeWidth="2.5"
                  strokeDasharray="5 3"
                  strokeLinecap="round"
                />
                <circle cx={fwdEndX} cy={fwdEndY} r="4" fill="var(--color-flare)" />
                <text x={fwdEndX + 8} y={fwdEndY + 4} fill="var(--color-flare)" fontFamily="var(--font-mono)" fontSize="10">
                  +24h
                </text>
              </g>
            )}

            {/* Bayesian Corrected Path */}
            {correctedPath && (
              <path
                d={correctedPath}
                fill="none"
                stroke="var(--color-white)"
                strokeWidth="2"
                strokeLinecap="round"
              />
            )}

            {/* Vessel Pin */}
            <g transform={`translate(${shipX}, ${shipY})`}>
              <circle cx="0" cy="0" r="10" fill="var(--color-inkwell)" stroke="var(--color-flare)" strokeWidth="2" />
              <circle cx="0" cy="0" r="3.5" fill="var(--color-flare)" />
              <text x="14" y="4" fill="var(--color-white)" fontFamily="var(--font-display)" fontSize="11" fontWeight="bold">
                {currentShip.name}
              </text>
            </g>
          </svg>

          {/* Compass Rose */}
          <div className="compass-rose">
            <span>N</span>
            <i />
            <span>S</span>
          </div>

          <div className="coordinate-readout">
            <Micro>
              {currentShip.current_position.lat.toFixed(4)}°N / {currentShip.current_position.lon.toFixed(4)}°E
            </Micro>
          </div>
        </div>

        {/* WAYPOINTS TABLE */}
        <div className="tactical-panel mt-3">
          <div className="flex justify-between items-center border-b border-line pb-2 mb-2">
            <Micro className="text-fog">PREDICTED DRIFT WAYPOINTS</Micro>
            <span className="font-mono text-micro text-fog">Step: 600s</span>
          </div>
          <table className="tactical-table">
            <thead>
              <tr>
                <th>Time Step</th>
                <th>Latitude</th>
                <th>Longitude</th>
                <th>Distance Advected</th>
              </tr>
            </thead>
            <tbody>
              {forward_track.slice(0, 6).map((pt, idx) => (
                <tr key={idx}>
                  <td className="font-bold text-flare">+{idx * 4}h</td>
                  <td className="text-white">{pt.lat.toFixed(4)}°N</td>
                  <td className="text-white">{pt.lon.toFixed(4)}°E</td>
                  <td className="text-fog">{(idx * 2.4).toFixed(1)} km</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* RIGHT INTELLIGENCE STACK */}
      <aside className="intelligence-stack">
        {/* Vessel Selector Ledger */}
        <section className="ledger">
          <div className="ledger-head">
            <div>
              <Micro className="text-flare">Fleet selector</Micro>
              <p className="mt-2 font-display text-xl font-medium">Suspect Vessels ({ships.length})</p>
            </div>
            <span className="grid size-10 place-items-center border border-flare/30 text-flare">
              <Icon name="crosshair" className="size-5" />
            </span>
          </div>

          <div className="mt-4 space-y-2">
            {ships.map((ship, index) => {
              const isActive = activeMmsi === ship.mmsi;
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
                      {ship.code} · <span className={isActive ? "text-flare font-bold" : ""}>{ship.state}</span>
                    </span>
                  </span>
                  <span className="risk-number">{ship.risk.toFixed(2)}</span>
                </Action>
              );
            })}
          </div>

          {/* Monte Carlo Bounds Card */}
          <div className="mt-4 pt-3 border-t border-line space-y-2 font-mono text-xs">
            <Micro className="text-tide">Monte Carlo Spatial Envelope</Micro>
            <div className="flex justify-between text-fog">
              <span>Lat Bounds:</span>
              <span className="text-white font-bold">
                {hindcast.bounds.lat[0].toFixed(3)}° – {hindcast.bounds.lat[1].toFixed(3)}°
              </span>
            </div>
            <div className="flex justify-between text-fog">
              <span>Lon Bounds:</span>
              <span className="text-white font-bold">
                {hindcast.bounds.lon[0].toFixed(3)}° – {hindcast.bounds.lon[1].toFixed(3)}°
              </span>
            </div>
          </div>
        </section>

        {/* Eco Card */}
        <section className="eco-card">
          <div className="eco-icon"><Icon name="shield" className="size-6 text-sun" /></div>
          <div className="min-w-0 flex-1">
            <Micro className="text-sun">Predicted Contact</Micro>
            <p className="mt-1 truncate font-display text-base font-semibold">Prongs Reef Sanctuary</p>
            <p className="mt-1 text-xs text-fog font-mono">ETA: <b className="text-white">+4.5h</b></p>
          </div>
        </section>
      </aside>

      {/* FOOTER */}
      <section className="case-footer">
        <span><Micro className="text-fog">Windage</Micro><b>0.03 (3.0%)</b></span>
        <span><Micro className="text-fog">Diffusion</Micro><b>2.0 M²/S</b></span>
        <span><Micro className="text-fog">Solver</Micro><b>RK4 INTEGRATION</b></span>
        <span className="case-footer-note">
          Simulated under Western Offshore hydrodynamics model.
        </span>
      </section>
    </div>
  );
}
