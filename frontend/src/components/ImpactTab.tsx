import { useState, useEffect, useId } from "react";
import { ShipData, ResponseQueueResult } from "../types";
import { Micro, Icon, Action } from "./Icon";

interface ImpactTabProps {
  ships: ShipData[];
  selectedMmsi: string;
  onSelectMmsi: (mmsi: string) => void;
  overallResponseQueue?: ResponseQueueResult;
}

export function ImpactTab({
  ships,
  selectedMmsi,
  onSelectMmsi,
  overallResponseQueue,
}: ImpactTabProps) {
  const [activeMmsi, setActiveMmsi] = useState<string>(selectedMmsi || ships[0]?.mmsi || "IND-7319");
  const [completedActions, setCompletedActions] = useState<Record<string, boolean>>({});
  const [simHour, setSimHour] = useState<number>(4.5);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [selectedZoneName, setSelectedZoneName] = useState<string | null>(null);
  const gradientId = useId();

  const currentShip = ships.find((s) => s.mmsi === activeMmsi) || ships[0];
  const primarySuspectShip = ships.find((s) => s.mmsi === "IND-7319") || ships[0];
  const forecast = currentShip.impact;
  const surveillance = currentShip.surveillance;
  const responseQueue =
    currentShip.response_queue?.response_queue || overallResponseQueue?.response_queue || [];

  const handleSelectShip = (mmsi: string) => {
    setActiveMmsi(mmsi);
    onSelectMmsi(mmsi);
  };

  const toggleAction = (id: string) => {
    setCompletedActions((prev) => ({
      ...prev,
      [id]: !prev[id],
    }));
  };

  // Play/Pause animation timer
  useEffect(() => {
    if (!isPlaying) return;
    const interval = setInterval(() => {
      setSimHour((prev) => {
        if (prev >= 24) {
          setIsPlaying(false);
          return 24;
        }
        return Math.min(24, Math.round((prev + 0.5) * 10) / 10);
      });
    }, 250);
    return () => clearInterval(interval);
  }, [isPlaying]);

  // Actual incident spill trajectory (starts at release position 19.00°N, 72.63°E and drifts towards Prongs Reef)
  const trajectory = primarySuspectShip.impact.sample_trajectory || [];

  // Interpolate current position along incident spill trajectory
  const getInterpolatedPoint = (h: number) => {
    if (!trajectory || trajectory.length === 0) {
      return { lat: 19.00, lon: 72.63 };
    }
    const firstH = trajectory[0].hours ?? 0;
    if (h <= firstH) return { lat: trajectory[0].lat, lon: trajectory[0].lon };
    const last = trajectory[trajectory.length - 1];
    const lastH = last.hours ?? 24;
    if (h >= lastH) return { lat: last.lat, lon: last.lon };

    for (let i = 0; i < trajectory.length - 1; i++) {
      const p1 = trajectory[i];
      const p2 = trajectory[i + 1];
      const p1H = p1.hours ?? 0;
      const p2H = p2.hours ?? 0;
      if (h >= p1H && h <= p2H) {
        const factor = (h - p1H) / (p2H - p1H || 1);
        return {
          lat: p1.lat + factor * (p2.lat - p1.lat),
          lon: p1.lon + factor * (p2.lon - p1.lon),
        };
      }
    }
    return { lat: last.lat, lon: last.lon };
  };

  const currentSlickPos = getInterpolatedPoint(simHour);

  // SVG Coordinate mapping (viewBox: 0 0 860 400)
  // Calibrated geographic bounds: Lon 72.50 to 72.95, Lat 18.70 to 19.30
  // Vertically stacks Mahim (North, Y: 70-130), Prongs Reef (Center, Y: 170-230), Malabar (South, Y: 250-310)
  const bMinLon = 72.50;
  const bMaxLon = 72.95;
  const bMinLat = 18.70;
  const bMaxLat = 19.30;

  const toMapX = (lon: number) => 70 + ((lon - bMinLon) / (bMaxLon - bMinLon)) * 680;
  const toMapY = (lat: number) => 350 - ((lat - bMinLat) / (bMaxLat - bMinLat)) * 300;

  // Active slick screen coords
  const slickX = toMapX(currentSlickPos.lon);
  const slickY = toMapY(currentSlickPos.lat);

  // Spill Origin (start of trajectory at 19.00°N, 72.63°E)
  const originPt = trajectory[0] || { lat: 19.00, lon: 72.63 };
  const originX = toMapX(originPt.lon);
  const originY = toMapY(originPt.lat);

  // Selected candidate ship position
  const selectedShipX = toMapX(currentShip.current_position.lon);
  const selectedShipY = toMapY(currentShip.current_position.lat);

  // Past path up to simHour
  const activePathPts = trajectory.filter((p) => (p.hours ?? 0) <= simHour);
  const pastPathStr = (() => {
    if (activePathPts.length === 0) return "";
    let d = `M ${toMapX(activePathPts[0].lon)} ${toMapY(activePathPts[0].lat)}`;
    for (let i = 1; i < activePathPts.length; i++) {
      d += ` L ${toMapX(activePathPts[i].lon)} ${toMapY(activePathPts[i].lat)}`;
    }
    d += ` L ${slickX} ${slickY}`;
    return d;
  })();

  // Future path beyond simHour
  const futurePathStr = (() => {
    if (simHour >= 24) return "";
    let d = `M ${slickX} ${slickY}`;
    const futurePts = trajectory.filter((p) => (p.hours ?? 0) > simHour);
    for (const p of futurePts) {
      d += ` L ${toMapX(p.lon)} ${toMapY(p.lat)}`;
    }
    return d;
  })();

  // Dispersion cloud expansion
  const spreadRadius = Math.min(34, 10 + Math.sqrt(simHour) * 4.2);

  // Preset quick scrubbers
  const presets = [
    { label: "T+0h Release", hour: 0 },
    { label: "T+4.5h Reef Intercept", hour: 4.5 },
    { label: "T+12h Core Sanctuary", hour: 12.0 },
    { label: "T+18h Coastal Approach", hour: 18.0 },
    { label: "T+24h Horizon", hour: 24.0 },
  ];

  // Specific GIS definitions for coastal zones (calibrated for zero visual collision)
  const zoneDefs = [
    {
      name: "Prongs Reef Sanctuary",
      minLon: 72.75,
      maxLon: 72.85,
      minLat: 18.94,
      maxLat: 19.06,
      eta: 4.5,
      weight: 1.0,
      type: "Coral Reef & Rocky Intertidal",
    },
    {
      name: "Malabar Marine Zone",
      minLon: 72.76,
      maxLon: 72.86,
      minLat: 18.76,
      maxLat: 18.88,
      eta: 15.5,
      weight: 0.85,
      type: "Pelagic Fisheries & Breeding Shelf",
    },
    {
      name: "Mahim Estuary Biosphere",
      minLon: 72.78,
      maxLon: 72.88,
      minLat: 19.12,
      maxLat: 19.24,
      eta: 16.0,
      weight: 0.90,
      type: "Tidal Mangroves & Mudflats",
    },
  ];

  const primaryZone = primarySuspectShip.impact.zones[0] || zoneDefs[0];

  return (
    <div className="mission-shell">
      {/* LEFT COORDINATE RAIL */}
      <aside className="coordinate-rail">
        <Micro className="rail-word">IMPACT ASSESSMENT</Micro>
        <span className="rail-line" />
        <span className="rail-number">{currentShip.current_position.lat.toFixed(2)}°N</span>
        <span className="rail-number">{currentShip.current_position.lon.toFixed(2)}°E</span>
        <span className="rail-number">{currentShip.code}</span>
      </aside>

      {/* CENTER OCEAN THEATRE */}
      <section className="ocean-theatre flex flex-col">
        <div className="theatre-heading">
          <div>
            <Micro className="text-fog">COASTAL SENSITIVITY & INTERCEPT · {currentShip.name}</Micro>
            <p className="mt-1 font-display text-3xl font-medium">Dynamic Dispersion Timeline</p>
          </div>
          <div className="slick-readout">
            <span>
              <Micro className="text-fog">Impact Index</Micro>
              <b className="text-sun">{forecast.impact_index.toFixed(2)}</b>
            </span>
            <span>
              <Micro className="text-fog">Elapsed Time</Micro>
              <b className="text-flare">+{simHour.toFixed(1)}H</b>
            </span>
            <span>
              <Micro className="text-fog">Ensemble Runs</Micro>
              <b>{forecast.ensemble_runs}</b>
            </span>
          </div>
        </div>

        {/* INTERACTIVE TIMELINE SCRUBBER BAR */}
        <div className="tactical-panel my-2 p-2.5 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setIsPlaying((p) => !p)}
              className={`px-3 py-1.5 font-mono text-xs font-bold rounded border cursor-pointer transition-all ${
                isPlaying
                  ? "bg-sun text-night border-sun"
                  : "bg-surface border-line text-white hover:border-sun"
              }`}
            >
              {isPlaying ? "PAUSE ❚❚" : "PLAY TIMELAPSE ▶"}
            </button>
            <button
              type="button"
              onClick={() => { setSimHour(0); setIsPlaying(false); }}
              className="px-2.5 py-1.5 font-mono text-micro rounded border border-line bg-surface text-fog hover:text-white cursor-pointer"
            >
              RESET
            </button>
          </div>

          <div className="flex-1 min-w-[200px] flex items-center gap-3">
            <span className="font-mono text-micro text-fog">0h</span>
            <input
              type="range"
              min="0"
              max="24"
              step="0.5"
              value={simHour}
              onChange={(e) => {
                setSimHour(parseFloat(e.target.value));
                setIsPlaying(false);
              }}
              className="flex-1 accent-sun cursor-pointer h-2 bg-surface rounded-lg appearance-none border border-line"
            />
            <span className="font-mono text-micro text-fog">+24h</span>
            <span className="font-mono text-sm font-bold text-sun w-14 text-right">
              +{simHour.toFixed(1)}h
            </span>
          </div>

          <div className="flex items-center gap-1.5">
            {presets.map((p, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => { setSimHour(p.hour); setIsPlaying(false); }}
                className={`px-2 py-1 font-mono text-micro rounded border cursor-pointer transition-all ${
                  Math.abs(simHour - p.hour) < 0.3
                    ? "bg-sun/20 border-sun text-sun font-bold"
                    : "bg-surface border-line text-fog hover:text-white"
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {/* DYNAMIC HYDRODYNAMIC DISPERSION MAP */}
        <div className="tactical-scope flex items-center justify-center p-2 relative">
          <svg className="w-full h-full max-h-[440px]" viewBox="0 0 860 400" aria-label="Ecological Intercept Map">
            <defs>
              <radialGradient id={`${gradientId}-slick`} cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor="var(--color-flare)" stopOpacity="0.85" />
                <stop offset="60%" stopColor="var(--color-sun)" stopOpacity="0.35" />
                <stop offset="100%" stopColor="var(--color-sun)" stopOpacity="0" />
              </radialGradient>
              <radialGradient id={`${gradientId}-hit`} cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor="var(--color-flare)" stopOpacity="0.35" />
                <stop offset="100%" stopColor="var(--color-flare)" stopOpacity="0.05" />
              </radialGradient>
            </defs>

            {/* Nautical Grids */}
            {Array.from({ length: 9 }).map((_, i) => (
              <line key={`igx-${i}`} x1={i * 105} y1="0" x2={i * 105} y2="400" stroke="var(--color-line)" strokeWidth="0.5" strokeDasharray="3 6" opacity="0.3" />
            ))}
            {Array.from({ length: 5 }).map((_, i) => (
              <line key={`igy-${i}`} x1="0" y1={i * 100} x2="860" y2={i * 100} stroke="var(--color-line)" strokeWidth="0.5" strokeDasharray="3 6" opacity="0.3" />
            ))}

            {/* Coastline (Mumbai Coastal Basin on Eastern Shore) */}
            <path
              d="M 720 0 L 750 60 L 730 130 L 760 210 L 740 290 L 775 350 L 760 400 L 860 400 L 860 0 Z"
              fill="oklch(85% 0.055 135)"
              opacity="0.85"
            />
            <path
              d="M 720 0 L 750 60 L 730 130 L 760 210 L 740 290 L 775 350 L 760 400"
              fill="none"
              stroke="var(--color-kelp)"
              strokeWidth="1.5"
            />
            <text x="770" y="50" fill="var(--color-fog)" fontFamily="var(--font-mono)" fontSize="11" letterSpacing="0.14em">
              MUMBAI
            </text>

            {/* COASTAL ECOSYSTEM ZONES (Vertically separated: Mahim North, Prongs Reef Center, Malabar South) */}
            {zoneDefs.map((zd, i) => {
              const x1 = toMapX(zd.minLon);
              const x2 = toMapX(zd.maxLon);
              const y1 = toMapY(zd.maxLat);
              const y2 = toMapY(zd.minLat);
              const w = Math.max(90, x2 - x1);
              const h = Math.max(50, y2 - y1);

              const zoneMatch = primarySuspectShip.impact.zones.find((z) =>
                z.name.toLowerCase().includes(zd.name.split(" ")[0].toLowerCase())
              );
              const exposure = zoneMatch ? zoneMatch.exposure_fraction : 0;

              // Physical Spatial Accuracy: Only highlight if the spill has reached the zone AND exposure is significant
              const isHit = (
                simHour >= zd.eta &&
                exposure >= 0.40 &&
                currentSlickPos.lon >= zd.minLon - 0.03
              );
              const isSelected = selectedZoneName === zd.name;

              return (
                <g
                  key={i}
                  transform={`translate(${x1}, ${y1})`}
                  onClick={() => setSelectedZoneName(zd.name)}
                  className="cursor-pointer"
                >
                  <rect
                    x="0"
                    y="0"
                    width={w}
                    height={h}
                    rx="4"
                    fill={isHit ? `url(#${gradientId}-hit)` : "color-mix(in oklch, var(--color-surface) 40%, transparent)"}
                    stroke={isHit ? "var(--color-flare)" : isSelected ? "var(--color-sun)" : "var(--color-line)"}
                    strokeWidth={isHit || isSelected ? "2" : "1"}
                    strokeDasharray={isHit ? "none" : "3 3"}
                  />
                  <text x="8" y="16" fill="var(--color-white)" fontFamily="var(--font-display)" fontSize="10.5" fontWeight="bold">
                    {zd.name.split(" ")[0].toUpperCase()} {zd.name.split(" ")[1]?.toUpperCase()}
                  </text>
                  <text x={w - 8} y="16" fill={isHit ? "var(--color-tide)" : "var(--color-fog)"} fontFamily="var(--font-mono)" fontSize="7.5" fontWeight="bold" textAnchor="end">
                    {isHit ? "BOOM DEPLOYED" : "BOOM LINE"}
                  </text>
                  <text
                    x="8"
                    y="30"
                    fill={isHit ? "var(--color-flare)" : "var(--color-sun)"}
                    fontFamily="var(--font-mono)"
                    fontSize="9.5"
                    fontWeight="bold"
                  >
                    {isHit ? `IMPACT ACTIVE: ${(exposure * 100).toFixed(0)}%` : `STANDBY (ETA: +${zd.eta.toFixed(1)}h)`}
                  </text>
                  <text x="8" y="44" fill="var(--color-fog)" fontFamily="var(--font-mono)" fontSize="8">
                    {zd.type.split("&")[0]}
                  </text>

                  {/* Containment Boom Barrier */}
                  <line
                    x1="-6"
                    y1="6"
                    x2="-6"
                    y2={h - 6}
                    stroke={isHit ? "var(--color-tide)" : "var(--color-line)"}
                    strokeWidth="2.5"
                    strokeDasharray={isHit ? "4 2" : "2 2"}
                  />
                </g>
              );
            })}

            {/* Traveled Spill Trajectory Path */}
            {pastPathStr && (
              <path
                d={pastPathStr}
                fill="none"
                stroke="var(--color-flare)"
                strokeWidth="2.5"
                strokeLinecap="round"
              />
            )}

            {/* Future Projection Path */}
            {futurePathStr && (
              <path
                d={futurePathStr}
                fill="none"
                stroke="var(--color-sun)"
                strokeWidth="1.5"
                strokeDasharray="4 4"
                opacity="0.6"
              />
            )}

            {/* Spill Origin Pin (Fixed Incident Release Point at 19.00°N, 72.63°E) */}
            <g transform={`translate(${originX}, ${originY})`}>
              <circle cx="0" cy="0" r="10" fill="var(--color-surface)" stroke="var(--color-flare)" strokeWidth="1.5" strokeDasharray="3 2" />
              <circle cx="0" cy="0" r="3.5" fill="var(--color-flare)" />
              <g transform="translate(-14, -6)">
                <text textAnchor="end" fill="var(--color-flare)" fontFamily="var(--font-mono)" fontSize="9" fontWeight="bold">
                  INCIDENT SPILL ORIGIN (T+0h)
                </text>
                <text textAnchor="end" y="12" fill="var(--color-fog)" fontFamily="var(--font-mono)" fontSize="8">
                  {originPt.lat.toFixed(3)}°N, {originPt.lon.toFixed(3)}°E · Release
                </text>
              </g>
            </g>

            {/* Selected Candidate Fleet Vessel Location Pin */}
            {currentShip.mmsi !== "IND-7319" && (
              <g transform={`translate(${selectedShipX}, ${selectedShipY})`}>
                <circle
                  cx="0"
                  cy="0"
                  r="10"
                  fill="var(--color-surface)"
                  stroke="var(--color-tide)"
                  strokeWidth="1.5"
                />
                <circle
                  cx="0"
                  cy="0"
                  r="3.5"
                  fill="var(--color-tide)"
                />
                <text x="14" y="-2" fill="var(--color-white)" fontFamily="var(--font-display)" fontSize="10.5" fontWeight="bold">
                  {currentShip.name} ({currentShip.code})
                </text>
                <text x="14" y="10" fill="var(--color-fog)" fontFamily="var(--font-mono)" fontSize="8">
                  {currentShip.state} · Excluded from Incident
                </text>
              </g>
            )}

            {/* Active Spill Ensemble / Dispersing Cloud */}
            <g transform={`translate(${slickX}, ${slickY})`}>
              <circle cx="0" cy="0" r={spreadRadius} fill={`url(#${gradientId}-slick)`} />
              <circle cx="0" cy="0" r="5" fill="var(--color-flare)" stroke="var(--color-white)" strokeWidth="1.5" />
              
              {/* Surrounding Dispersed Lagrangian Particles */}
              {[-12, -4, 8, 14].map((dx, pIdx) => {
                const dy = (pIdx % 2 === 0 ? 1 : -1) * (6 + pIdx * 3);
                return (
                  <circle
                    key={pIdx}
                    cx={dx * (spreadRadius / 16)}
                    cy={dy * (spreadRadius / 16)}
                    r="2"
                    fill="var(--color-sun)"
                    opacity="0.8"
                  />
                );
              })}

              {/* Non-overlapping HUD Callout cleanly floating above the slick */}
              <g transform={`translate(0, ${-spreadRadius - 20})`}>
                <line x1="0" y1="20" x2="0" y2="4" stroke="var(--color-flare)" strokeWidth="1" strokeDasharray="2 2" />
                <rect x="-85" y="-14" width="170" height="25" rx="3" fill="var(--color-night)" stroke="var(--color-flare)" strokeWidth="1" opacity="0.95" />
                <text textAnchor="middle" y="-2" fill="var(--color-flare)" fontFamily="var(--font-mono)" fontSize="9" fontWeight="bold">
                  MUM-04 ENSEMBLE (T+{simHour.toFixed(1)}h)
                </text>
                <text textAnchor="middle" y="8" fill="var(--color-fog)" fontFamily="var(--font-mono)" fontSize="7.5">
                  {currentSlickPos.lat.toFixed(3)}°N, {currentSlickPos.lon.toFixed(3)}°E · Spread: ±{(spreadRadius * 40).toFixed(0)}m
                </text>
              </g>
            </g>
          </svg>

          <div className="coordinate-readout">
            <Micro>
              Simulation Horizon: T+{simHour.toFixed(1)}h · Lat: {currentSlickPos.lat.toFixed(3)}°N / Lon: {currentSlickPos.lon.toFixed(3)}°E
            </Micro>
          </div>
        </div>

        {/* ECOLOGICAL SENSITIVITY ZONES CARDS */}
        <div className="tactical-panel mt-3">
          <div className="flex justify-between items-center border-b border-line pb-2 mb-2">
            <Micro className="text-sun">CRITICAL HABITAT EXPOSURE AUDIT</Micro>
            <span className="font-mono text-micro text-fog">Click zone to inspect barrier plan</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {zoneDefs.map((zd, i) => {
              const zoneMatch = primarySuspectShip.impact.zones.find((z) =>
                z.name.toLowerCase().includes(zd.name.split(" ")[0].toLowerCase())
              );
              const exposure = zoneMatch ? zoneMatch.exposure_fraction : 0;
              const expPct = Math.round(exposure * 100);
              const isHit = (
                simHour >= zd.eta &&
                exposure >= 0.40 &&
                currentSlickPos.lon >= zd.minLon - 0.03
              );
              const isSelected = selectedZoneName === zd.name;

              return (
                <div
                  key={i}
                  onClick={() => setSelectedZoneName(zd.name)}
                  className={`p-3 border rounded space-y-2 font-mono text-xs cursor-pointer transition-all ${
                    isHit
                      ? "bg-flare/10 border-flare shadow-sm"
                      : isSelected
                      ? "bg-sun/10 border-sun"
                      : "bg-surface border-line hover:border-fog"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 truncate">
                      <Icon name="shield" className={`size-4 ${isHit ? "text-flare" : "text-sun"}`} />
                      <h5 className="font-display text-sm font-bold text-white truncate">{zd.name}</h5>
                    </div>
                    {isHit && <span className="badge-flare text-micro">CRITICAL HIT</span>}
                  </div>

                  <div className="pt-2 border-t border-line/40 space-y-1">
                    <div className="flex justify-between">
                      <span className="text-fog">Exposure Risk:</span>
                      <span className={`font-bold ${isHit ? "text-flare" : expPct > 0 ? "text-sun" : "text-fog"}`}>
                        {expPct}%
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-fog">Earliest Intercept:</span>
                      <span className="text-white">+{zd.eta.toFixed(1)}h</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-fog">Habitat Type:</span>
                      <span className="text-fog truncate max-w-[140px]">{zd.type}</span>
                    </div>
                    <div className="flex justify-between pt-1 border-t border-line/20">
                      <span className="text-fog">Containment Status:</span>
                      <span className={`font-bold ${isHit ? "text-tide" : "text-fog"}`}>
                        {isHit ? "BOOMS DEPLOYED" : "DEFENSE READY"}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* OPERATIONAL RESPONSE TASKFORCE QUEUE */}
        {responseQueue.length > 0 && (
          <div className="tactical-panel mt-3">
            <div className="flex justify-between items-center border-b border-line pb-2 mb-2">
              <Micro className="text-flare">CONTAINMENT ACTION QUEUE · DISPATCH ORDERS</Micro>
              <span className="font-mono text-micro text-fog">{responseQueue.length} Zones Assigned</span>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
              {responseQueue.map((item, qIdx) => (
                <div key={qIdx} className="border border-line bg-surface p-3 rounded space-y-2">
                  <div className="flex justify-between items-center border-b border-line/40 pb-1.5">
                    <span className="font-display text-sm font-bold text-white">{item.zone}</span>
                    <span className="badge-sun">Priority #{item.priority_rank}</span>
                  </div>

                  <div className="space-y-1">
                    {item.recommended_actions.map((act, aIdx) => {
                      const key = `${item.zone}-${aIdx}`;
                      const isDone = !!completedActions[key];

                      return (
                        <div
                          key={aIdx}
                          onClick={() => toggleAction(key)}
                          className={`flex items-start gap-2 p-1.5 rounded border transition-all cursor-pointer text-xs font-mono ${
                            isDone
                              ? "bg-tide/10 border-tide/50 text-white line-through opacity-70"
                              : "bg-inkwell border-line text-white hover:border-tide"
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={isDone}
                            onChange={() => {}}
                            className="mt-0.5 accent-tide cursor-pointer"
                          />
                          <span className="flex-1">{act}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </section>

      {/* RIGHT INTELLIGENCE STACK */}
      <aside className="intelligence-stack">
        {/* Vessel Selector Ledger */}
        <section className="ledger">
          <div className="ledger-head">
            <div>
              <Micro className="text-sun">Risk Triage</Micro>
              <p className="mt-2 font-display text-xl font-medium">Fleet Triage ({ships.length})</p>
            </div>
            <span className="grid size-10 place-items-center border border-sun/30 text-sun">
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
                      {ship.code} · Impact: <b className="text-sun">{ship.impact.impact_index.toFixed(2)}</b>
                    </span>
                  </span>
                  <span className="risk-number">{ship.risk.toFixed(2)}</span>
                </Action>
              );
            })}
          </div>

          {/* Surveillance Priority Breakdown */}
          <div className="mt-4 pt-3 border-t border-line space-y-2 font-mono text-xs">
            <Micro className="text-fog">Surveillance Priority</Micro>
            <div className="flex justify-between text-fog">
              <span>Priority Index:</span>
              <span className="text-flare font-bold">{surveillance.priority_index.toFixed(3)}</span>
            </div>
            <div className="flex justify-between text-fog">
              <span>Behavior Risk:</span>
              <span className="text-white font-bold">{surveillance.behavior_index.toFixed(2)}</span>
            </div>
            <div className="flex justify-between text-fog">
              <span>Spill Opportunity:</span>
              <span className="text-white font-bold">{surveillance.spill_opportunity.toFixed(2)}</span>
            </div>
          </div>
        </section>

        {/* Immediate Eco Intercept Card */}
        <section className="eco-card">
          <div className="eco-icon"><Icon name="shield" className="size-6 text-sun" /></div>
          <div className="min-w-0 flex-1">
            <Micro className="text-sun">Immediate Intercept</Micro>
            <p className="mt-1 truncate font-display text-base font-semibold">{primaryZone?.name || "Coastal Reserve"}</p>
            <p className="mt-1 text-xs text-fog font-mono">
              Exposure: <b className="text-white">{((primaryZone?.exposure_fraction || 0) * 100).toFixed(0)}%</b>
            </p>
          </div>
          <span className="font-mono text-lg text-sun">
            {primaryZone?.earliest_eta_hours ? `+${primaryZone.earliest_eta_hours.toFixed(1)}h` : "N/A"}
          </span>
        </section>
      </aside>

      {/* FOOTER */}
      <section className="case-footer">
        <span><Micro className="text-fog">Impact Index</Micro><b className="text-sun">{forecast.impact_index.toFixed(2)}</b></span>
        <span><Micro className="text-fog">Endangered Zone</Micro><b>{primaryZone?.name || "Coastal Reserve"}</b></span>
        <span><Micro className="text-fog">Earliest ETA</Micro><b>+{primaryZone?.earliest_eta_hours || 4.5}H</b></span>
        <span className="case-footer-note">
          Lagrangian particles intersected with coastal sensitive GIS polygons. Interactive time scrubber: T+{simHour.toFixed(1)}h.
        </span>
      </section>
    </div>
  );
}
