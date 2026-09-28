import { useState, useId } from "react";
import { ShipData } from "../types";
import { Icon, Micro } from "./Icon";

interface SonarMapProps {
  ships: ShipData[];
  selectedMmsi: string;
  onSelectMmsi: (mmsi: string) => void;
}

// Transform geographic coords to 600x600 SVG tactical space
export function projectToSvg(lat: number, lon: number): [number, number] {
  const minLat = 18.60, maxLat = 19.45;
  const minLon = 72.35, maxLon = 72.90;
  const x = 50 + ((lon - minLon) / (maxLon - minLon)) * 470;
  const y = 550 - ((lat - minLat) / (maxLat - minLat)) * 500;
  return [
    Math.round(Math.max(25, Math.min(575, x))),
    Math.round(Math.max(25, Math.min(575, y)))
  ];
}

function pointsToSvgPath(points: { lat: number; lon: number }[]): string {
  if (!points || points.length === 0) return "";
  const svgCoords = points.map(p => projectToSvg(p.lat, p.lon));
  let d = `M ${svgCoords[0][0]} ${svgCoords[0][1]}`;
  for (let i = 1; i < svgCoords.length; i++) {
    d += ` L ${svgCoords[i][0]} ${svgCoords[i][1]}`;
  }
  return d;
}

export function SonarMap({ ships, selectedMmsi, onSelectMmsi }: SonarMapProps) {
  const [showForecast, setShowForecast] = useState(true);
  const [showBacktrack, setShowBacktrack] = useState(true);
  const [showHindcastCloud, setShowHindcastCloud] = useState(false);
  const gradientId = useId();

  const selectedShip = ships.find(s => s.mmsi === selectedMmsi) || ships[0];

  // Selected ship forecast & backtrack paths
  const forecastPath = selectedShip ? pointsToSvgPath(selectedShip.drift_forecast.forward_track) : "";
  const backtrackPath = selectedShip ? pointsToSvgPath(selectedShip.drift_backtrack.backtrack_track) : "";

  // Hindcast origin points projected
  const originPoints = selectedShip?.drift_backtrack.hindcast.origins.map(o => {
    const [x, y] = projectToSvg(o.lat, o.lon);
    return { x, y, hours: o.hours_before };
  }) || [];

  return (
    <div className="flex flex-col items-center w-full">
      {/* Minimal clean simulation layer toggles */}
      <div className="flex flex-wrap gap-2 mb-2 items-center justify-center z-10 text-xs font-mono">
        <button
          type="button"
          onClick={() => setShowForecast(v => !v)}
          className={`px-2.5 py-0.5 border rounded transition-all cursor-pointer ${
            showForecast ? "bg-flare/20 border-flare text-flare font-medium" : "border-line text-fog bg-surface/30"
          }`}
        >
          Forecast (+24h)
        </button>
        <button
          type="button"
          onClick={() => setShowBacktrack(v => !v)}
          className={`px-2.5 py-0.5 border rounded transition-all cursor-pointer ${
            showBacktrack ? "bg-tide/20 border-tide text-tide font-medium" : "border-line text-fog bg-surface/30"
          }`}
        >
          Backtrack (-8h)
        </button>
        <button
          type="button"
          onClick={() => setShowHindcastCloud(v => !v)}
          className={`px-2.5 py-0.5 border rounded transition-all cursor-pointer ${
            showHindcastCloud ? "bg-sun/20 border-sun text-sun font-medium" : "border-line text-fog bg-surface/30"
          }`}
        >
          Origins Cloud
        </button>
      </div>

      <div className="sonar-stage relative">
        <div className="sonar-orbit orbit-one" />
        <div className="sonar-orbit orbit-two" />
        <div className="sonar-orbit orbit-three" />
        <div className="sonar-axis axis-x" />
        <div className="sonar-axis axis-y" />
        <div className="sonar-sweep" />

        <svg className="chart-coast" viewBox="0 0 600 600" aria-label="Mumbai offshore tactical sonar">
          <defs>
            <linearGradient id={`${gradientId}-forecast`} x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="var(--color-flare)" stopOpacity="0.9" />
              <stop offset="100%" stopColor="var(--color-sun)" stopOpacity="0.3" />
            </linearGradient>
            <linearGradient id={`${gradientId}-backtrack`} x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="var(--color-tide)" stopOpacity="0.9" />
              <stop offset="100%" stopColor="var(--color-fog)" stopOpacity="0.2" />
            </linearGradient>
          </defs>

          {/* Mumbai coastline & terrain */}
          <path className="coast-fill" d="M492-10h130v630H470l18-44-21-49 27-46-18-50 31-39-23-47 29-44-20-51 32-44-25-51 21-47-26-49Z" />
          <path className="coast-line" d="M492-10l3 49 26 49-21 47 25 51-32 44 20 51-29 44 23 47-31 39 18 50-27 46 21 49-18 44" />
          
          {/* Shipping lanes */}
          <path className="route-line" d="M45 480c119-56 158-111 248-132 84-20 133-88 211-173" />
          <path className="route-line route-secondary" d="M52 186c102 29 174 15 255-30 65-36 129-45 199-39" />
          
          {/* Sensitive Ecological Reserve Zone */}
          <g className="eco-polygon">
            <path d="M418 391c34-15 66-3 73 25-15 34-47 44-79 21-9-20-7-34 6-46Z" />
            <text x="427" y="419">PRONGS REEF</text>
          </g>
          
          {/* Geographic labels */}
          <text className="chart-label" x="518" y="170">MUMBAI</text>
          <text className="chart-label sea-label" x="95" y="390">ARABIAN SEA</text>

          {/* Dynamic Selected Ship Backtrack Trajectory */}
          {showBacktrack && backtrackPath && (
            <g className="backtrack-layer">
              <path
                d={backtrackPath}
                fill="none"
                stroke={`url(#${gradientId}-backtrack)`}
                strokeWidth="2"
                strokeDasharray="4 4"
                strokeLinecap="round"
                className="opacity-75"
              />
            </g>
          )}

          {/* Dynamic Selected Ship Forward Forecast Trajectory */}
          {showForecast && forecastPath && (
            <g className="forecast-layer">
              <path
                d={forecastPath}
                fill="none"
                stroke={`url(#${gradientId}-forecast)`}
                strokeWidth="2.5"
                strokeDasharray="5 3"
                strokeLinecap="round"
                className="opacity-85"
              />
            </g>
          )}

          {/* Monte Carlo Origin Cloud (optional layer) */}
          {showHindcastCloud && originPoints.length > 0 && (
            <g className="hindcast-origins-layer">
              {originPoints.map((pt, i) => (
                <circle
                  key={i}
                  cx={pt.x}
                  cy={pt.y}
                  r="2"
                  fill="var(--color-sun)"
                  opacity="0.4"
                />
              ))}
            </g>
          )}

          {/* Observed spill slick centroid */}
          <g className="observed-spill">
            <circle cx="282" cy="328" r="7" fill="var(--color-flare)" fillOpacity="0.2" stroke="var(--color-flare)" strokeWidth="1" strokeDasharray="3 3" />
            <circle cx="282" cy="328" r="2.5" fill="var(--color-flare)" />
            <text x="294" y="332" fill="var(--color-flare)" fontFamily="var(--font-mono)" fontSize="9" letterSpacing="0.08em">MUM-04 SLICK</text>
          </g>
        </svg>

        {/* SHIP ICONS AT CURRENT LOCATIONS (CLEAN, NO EXPANDING CIRCLE ANIMATIONS, NO CLUTTER) */}
        {ships.map((ship) => {
          const isSelected = selectedMmsi === ship.mmsi;
          const [x, y] = projectToSvg(ship.current_position.lat, ship.current_position.lon);
          const leftPct = (x / 600) * 100;
          const topPct = (y / 600) * 100;

          return (
            <button
              key={ship.mmsi}
              type="button"
              title={`${ship.name} (${ship.code}) · Risk: ${ship.risk} · ${ship.state}`}
              onClick={() => onSelectMmsi(ship.mmsi)}
              className={`absolute z-10 size-8 -translate-x-1/2 -translate-y-1/2 rounded-full flex items-center justify-center transition-all cursor-pointer ${
                isSelected
                  ? "bg-flare text-night ring-2 ring-white shadow-md scale-110"
                  : "bg-inkwell text-tide border border-line hover:border-tide hover:scale-105 shadow-sm"
              }`}
              style={{
                left: `${leftPct}%`,
                top: `${topPct}%`,
              }}
            >
              <Icon name="vessel" className="size-4" />
            </button>
          );
        })}

        <div className="sonar-center">
          <span className="size-2 rounded-full bg-tide" />
          <Micro className="text-tide">M-7</Micro>
        </div>

        <div className="compass-rose"><span>N</span><i /><span>S</span></div>

        {/* Selected target metadata caption (clean, contained at bottom left) */}
        {selectedShip && (
          <div className="sonar-caption">
            <Micro className="text-fog">Active vessel</Micro>
            <p className="mt-1 font-display text-2xl font-semibold text-white">{selectedShip.name}</p>
            <div className="mt-2 flex gap-4 text-xs">
              <span><Micro className="text-fog">Bearing</Micro><b className="ml-1.5 font-mono text-tide">{selectedShip.bearing}</b></span>
              <span><Micro className="text-fog">SOG</Micro><b className="ml-1.5 font-mono text-tide">{selectedShip.speed}</b></span>
              <span><Micro className="text-fog">Status</Micro><b className="ml-1.5 font-mono text-flare">{selectedShip.state}</b></span>
            </div>
          </div>
        )}

        {/* Selected vessel coordinate readout (bottom right) */}
        {selectedShip && (
          <div className="coordinate-readout">
            <Micro>{selectedShip.current_position.lat.toFixed(4)} N / {selectedShip.current_position.lon.toFixed(4)} E</Micro>
          </div>
        )}
      </div>
    </div>
  );
}
