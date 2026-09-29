import { useState } from "react";
import { ShipData, DeadReckoningResult, ObservationPlanResult, EscapeInterceptResult, AisTrustResult } from "../types";
import { Micro, Icon, Action } from "./Icon";

interface SatelliteTabProps {
  ships?: ShipData[];
  selectedMmsi?: string;
  onSelectMmsi?: (mmsi: string) => void;
  deadReckoning?: DeadReckoningResult;
  observationPlan?: ObservationPlanResult;
  escapeIntercept?: EscapeInterceptResult;
  aisTrust?: AisTrustResult;
}

export function SatelliteTab({
  ships = [],
  selectedMmsi,
  onSelectMmsi,
  deadReckoning,
  observationPlan,
  escapeIntercept,
  aisTrust,
}: SatelliteTabProps) {
  const [activeMmsi, setActiveMmsi] = useState<string>(selectedMmsi || ships[0]?.mmsi || "IND-7319");
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);

  const currentShip = ships.find((s) => s.mmsi === activeMmsi) || ships[0];
  const matches = deadReckoning?.matches || [];
  const primaryMatch = matches[0];
  const rankedWindows = observationPlan?.ranked_windows || [];
  const recommendedWindow = observationPlan?.recommended_observation_window || rankedWindows[0];
  const [taskedWindow, setTaskedWindow] = useState<string | null>(recommendedWindow?.time || null);

  const handleSelectShip = (mmsi: string) => {
    setActiveMmsi(mmsi);
    setSelectedEventId(null);
    if (onSelectMmsi) onSelectMmsi(mmsi);
  };

  const isPragati = currentShip?.mmsi === "IND-7319";
  const isOceanCrest = currentShip?.mmsi === "MHL-4420";

  // Build structured historical breadcrumb events for each vessel
  const breadcrumbHistory = (() => {
    if (isPragati) {
      return [
        {
          id: "prg-1",
          time: "06:00 UTC",
          lat: 18.850,
          lon: 72.550,
          sog: "12.4 kn",
          cog: "118°",
          type: "nominal",
          label: "Nominal AIS Transit",
          detail: "Transponder active. Normal open-water passage speed and route.",
        },
        {
          id: "prg-2",
          time: "06:30 UTC",
          lat: 18.855,
          lon: 72.555,
          sog: "12.1 kn",
          cog: "120°",
          type: "nominal",
          label: "Nominal AIS Transit",
          detail: "Continuous ping. Steady heading towards offshore channel.",
        },
        {
          id: "prg-3",
          time: "07:00 UTC",
          lat: 18.860,
          lon: 72.560,
          sog: "12.0 kn",
          cog: "122°",
          type: "nominal",
          label: "Nominal AIS Transit",
          detail: "Standard telemetry beacon. Speed consistent with tanker profile.",
        },
        {
          id: "prg-4",
          time: "07:50 UTC",
          lat: 18.871,
          lon: 72.571,
          sog: "3.2 kn",
          cog: "135°",
          type: "gap",
          label: "AIS SILENCE INITIATED (BLACKOUT)",
          detail: "Transponder deliberately switched OFF. Vessel went dark for 15 minutes immediately following discharge.",
        },
        {
          id: "prg-5",
          time: "08:05 UTC",
          lat: 19.000,
          lon: 72.630,
          sog: "31.4 kn",
          cog: "045°",
          type: "spoofed",
          label: "FALSE / SPOOFED LOCATION BROADCAST",
          detail: "Transponder re-activated at fabricated position. Required impossible 31.4 knot speed jump across 15 minutes.",
        },
        {
          id: "prg-6",
          time: "08:05 UTC",
          lat: 19.000,
          lon: 72.718,
          sog: "11.2 kn",
          cog: "118°",
          type: "sar",
          label: "SENTINEL-1 SAR RADAR INTERCEPT",
          detail: "Spaceborne C-band radar captured metallic ship echo during blackout. Dead reckoning matches contact within 7.9 meters.",
        },
      ];
    } else if (isOceanCrest) {
      return [
        {
          id: "oc-1",
          time: "06:00 UTC",
          lat: 18.705,
          lon: 72.475,
          sog: "2.1 kn",
          cog: "115°",
          type: "nominal",
          label: "Offshore Loitering Ping",
          detail: "Vessel holding station in southern anchorage area.",
        },
        {
          id: "oc-2",
          time: "06:30 UTC",
          lat: 18.708,
          lon: 72.478,
          sog: "1.8 kn",
          cog: "118°",
          type: "nominal",
          label: "Station-Keeping Ping",
          detail: "Continuous valid AIS telemetry broadcast.",
        },
        {
          id: "oc-3",
          time: "07:15 UTC",
          lat: 18.712,
          lon: 72.482,
          sog: "2.5 kn",
          cog: "120°",
          type: "nominal",
          label: "Low-Speed Maneuvering",
          detail: "No transponder gap recorded. Zero kinematic discrepancies.",
        },
        {
          id: "oc-4",
          time: "08:30 UTC",
          lat: 18.725,
          lon: 72.495,
          sog: "3.4 kn",
          cog: "118°",
          type: "nominal",
          label: "Nominal Current Position",
          detail: "Position verified by coastal radar. Eliminated from slick source attribution.",
        },
      ];
    } else {
      return [
        {
          id: "mr-1",
          time: "06:00 UTC",
          lat: 19.200,
          lon: 72.380,
          sog: "14.8 kn",
          cog: "032°",
          type: "nominal",
          label: "Container Inbound Transit",
          detail: "High-speed container transit on northern shipping lane.",
        },
        {
          id: "mr-2",
          time: "06:45 UTC",
          lat: 19.255,
          lon: 72.425,
          sog: "13.9 kn",
          cog: "035°",
          type: "nominal",
          label: "Route Deviation Ping",
          detail: "Minor course change to clear outbound traffic.",
        },
        {
          id: "mr-3",
          time: "07:30 UTC",
          lat: 19.310,
          lon: 72.470,
          sog: "12.8 kn",
          cog: "030°",
          type: "nominal",
          label: "Transit Channel Ping",
          detail: "Continuous telemetry. 35 km north of observed oil discharge.",
        },
        {
          id: "mr-4",
          time: "08:15 UTC",
          lat: 19.360,
          lon: 72.510,
          sog: "11.8 kn",
          cog: "032°",
          type: "nominal",
          label: "Current AIS Fix",
          detail: "Zero physical consistency with slick MUM-04 backtrack trajectory.",
        },
      ];
    }
  })();

  // Calibrated projection bounds for SVG Radar Scope (viewBox 0 0 860 400)
  // Ensures all callouts, cones, and telemetry tags have ample breathing room without overlapping
  const bMinLon = isPragati ? 72.520 : Math.min(...breadcrumbHistory.map((p) => p.lon)) - 0.04;
  const bMaxLon = isPragati ? 72.750 : Math.max(...breadcrumbHistory.map((p) => p.lon)) + 0.04;
  const bMinLat = isPragati ? 18.825 : Math.min(...breadcrumbHistory.map((p) => p.lat)) - 0.03;
  const bMaxLat = isPragati ? 19.040 : Math.max(...breadcrumbHistory.map((p) => p.lat)) + 0.03;

  const toMapX = (lon: number) => 90 + ((lon - bMinLon) / (bMaxLon - bMinLon)) * 670;
  const toMapY = (lat: number) => 340 - ((lat - bMinLat) / (bMaxLat - bMinLat)) * 260;

  // Active match metrics
  const corridorBudgetUsed = primaryMatch
    ? ((primaryMatch.detection_distance_m / primaryMatch.corridor_radius_m) * 100).toFixed(1)
    : "0.6";

  // Coordinates for Pragati key nodes
  const gapX = toMapX(72.571);
  const gapY = toMapY(18.871);
  const spoofX = toMapX(72.630);
  const spoofY = toMapY(19.000);
  const sarX = toMapX(72.718);
  const sarY = toMapY(19.000);

  const midJumpX = (gapX + spoofX) / 2;
  const midJumpY = (gapY + spoofY) / 2;

  return (
    <div className="mission-shell">
      {/* LEFT COORDINATE RAIL */}
      <aside className="coordinate-rail">
        <Micro className="rail-word">RADAR RECON</Micro>
        <span className="rail-line" />
        <span className="rail-number">{currentShip?.current_position.lat.toFixed(2) || "19.00"}°N</span>
        <span className="rail-number">{currentShip?.current_position.lon.toFixed(2) || "72.72"}°E</span>
        <span className="rail-number">{currentShip?.code || "S1-CSAR"}</span>
      </aside>

      {/* CENTER OCEAN THEATRE */}
      <section className="ocean-theatre flex flex-col">
        <div className="theatre-heading">
          <div>
            <Micro className="text-fog">SPACEBORNE SAR RECONNAISSANCE · {currentShip?.name}</Micro>
            <p className="mt-1 font-display text-3xl font-medium">Historical Breadcrumbs & Blackout Correlation</p>
          </div>
          <div className="slick-readout">
            <span>
              <Micro className="text-fog">Historical Pings</Micro>
              <b>{breadcrumbHistory.length} EVENTS</b>
            </span>
            <span>
              <Micro className="text-fog">AIS Status</Micro>
              <b className={isPragati ? "text-flare" : "text-tide"}>
                {isPragati ? "BLACKOUT & SPOOF" : "CONTINUOUS NOMINAL"}
              </b>
            </span>
            <span>
              <Micro className="text-fog">SAR Echo Residual</Micro>
              <b className="text-sun">{isPragati ? "7.9 M" : "N/A"}</b>
            </span>
          </div>
        </div>

        {/* SATELLITE RADAR SCOPE DISPLAY */}
        <div className="tactical-scope flex items-center justify-center p-3 relative">
          <svg className="w-full h-full max-h-[440px]" viewBox="0 0 860 400" aria-label="SAR Radar Scope">
            <defs>
              <radialGradient id="scopeGlow" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor="var(--color-tide)" stopOpacity="0.12" />
                <stop offset="100%" stopColor="var(--color-tide)" stopOpacity="0" />
              </radialGradient>
              <radialGradient id="sarHitGlow" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor="var(--color-flare)" stopOpacity="0.6" />
                <stop offset="100%" stopColor="var(--color-flare)" stopOpacity="0" />
              </radialGradient>
            </defs>

            {/* Radar Range Rings */}
            <circle cx="430" cy="200" r="180" fill="none" stroke="var(--color-line)" strokeWidth="0.8" strokeDasharray="4 4" opacity="0.3" />
            <circle cx="430" cy="200" r="115" fill="none" stroke="var(--color-line)" strokeWidth="0.8" strokeDasharray="3 3" opacity="0.4" />
            <circle cx="430" cy="200" r="55" fill="none" stroke="var(--color-line)" strokeWidth="0.8" opacity="0.5" />
            <line x1="60" y1="200" x2="800" y2="200" stroke="var(--color-line)" strokeWidth="0.8" strokeDasharray="3 4" opacity="0.25" />
            <line x1="430" y1="20" x2="430" y2="380" stroke="var(--color-line)" strokeWidth="0.8" strokeDasharray="3 4" opacity="0.25" />

            {/* Satellite Orbital Vector */}
            <path d="M 60 40 L 780 340" stroke="var(--color-tide)" strokeWidth="1" strokeDasharray="6 4" opacity="0.4" />
            <text x="75" y="55" fill="var(--color-tide)" fontFamily="var(--font-mono)" fontSize="10">
              SENTINEL-1 ORBIT 4821 (CSAR INTERCEPT)
            </text>

            {/* Swath Beam */}
            <polygon
              points="160,35 560,35 680,355 280,355"
              fill="url(#scopeGlow)"
              stroke="var(--color-tide)"
              strokeWidth="0.8"
              strokeDasharray="4 4"
              opacity="0.35"
            />

            {/* If Pragati: Dead-Reckoning Corridor Cone and Impossible Jump Vector */}
            {isPragati && (
              <g>
                {/* Kinematic Dead-Reckoning Corridor Cone from Gap to SAR Echo */}
                <polygon
                  points={`${gapX},${gapY} ${sarX - 18},${sarY - 30} ${sarX + 18},${sarY + 30}`}
                  fill="color-mix(in oklch, var(--color-sun) 10%, transparent)"
                  stroke="var(--color-sun)"
                  strokeWidth="1"
                  strokeDasharray="3 3"
                />
                <text
                  x={(gapX + sarX) / 2 + 15}
                  y={(gapY + sarY) / 2 + 14}
                  fill="var(--color-sun)"
                  fontFamily="var(--font-mono)"
                  fontSize="8"
                  opacity="0.85"
                >
                  DEAD RECKONING CORRIDOR (±1360m)
                </text>

                {/* Impossible Jump Vector from Gap to Spoofed Location */}
                <line
                  x1={gapX}
                  y1={gapY}
                  x2={spoofX}
                  y2={spoofY}
                  stroke="var(--color-flare)"
                  strokeWidth="2"
                  strokeDasharray="4 2"
                />

                {/* Floating Violation Badge midway along jump line */}
                <g transform={`translate(${midJumpX - 55}, ${midJumpY - 14})`}>
                  <rect x="0" y="0" width="115" height="20" rx="3" fill="var(--color-surface)" stroke="var(--color-flare)" strokeWidth="1" />
                  <text x="57" y="14" fill="var(--color-flare)" fontFamily="var(--font-mono)" fontSize="8.5" fontWeight="bold" textAnchor="middle">
                    ⚡ +31.4 kn VIOLATION
                  </text>
                </g>
              </g>
            )}

            {/* Historical AIS Breadcrumb Connecting Path */}
            {breadcrumbHistory.length > 1 && (
              <path
                d={breadcrumbHistory
                  .filter((p) => p.type !== "sar")
                  .map((p, i) => `${i === 0 ? "M" : "L"} ${toMapX(p.lon)} ${toMapY(p.lat)}`)
                  .join(" ")}
                fill="none"
                stroke="var(--color-tide)"
                strokeWidth="1.5"
                strokeDasharray="3 3"
                opacity="0.6"
              />
            )}

            {/* Breadcrumb Markers with Clean, Non-Overlapping Tactical Callouts */}
            {breadcrumbHistory.map((item, idx) => {
              const x = toMapX(item.lon);
              const y = toMapY(item.lat);
              const isSelected = selectedEventId === item.id;

              // 1. Nominal AIS pings: subtle dots without clashing text
              if (item.type === "nominal") {
                const isFirst = idx === 0;
                return (
                  <g
                    key={item.id}
                    transform={`translate(${x}, ${y})`}
                    onClick={() => setSelectedEventId(item.id)}
                    className="cursor-pointer"
                  >
                    <circle cx="0" cy="0" r={isSelected ? "6" : "4"} fill="var(--color-tide)" stroke={isSelected ? "var(--color-white)" : "none"} strokeWidth="1.5" />
                    {isFirst && (
                      <text x="-8" y="16" fill="var(--color-fog)" fontFamily="var(--font-mono)" fontSize="9" textAnchor="middle">
                        {item.time} ({item.sog})
                      </text>
                    )}
                  </g>
                );
              }

              // 2. AIS Silence Initiated: Left-anchored callout box (completely clear of other points)
              if (item.type === "gap") {
                return (
                  <g
                    key={item.id}
                    transform={`translate(${x}, ${y})`}
                    onClick={() => setSelectedEventId(item.id)}
                    className="cursor-pointer"
                  >
                    {/* Amber Diamond Marker */}
                    <polygon
                      points="0,-8 8,0 0,8 -8,0"
                      fill="var(--color-sun)"
                      stroke="var(--color-white)"
                      strokeWidth="1.5"
                    />
                    
                    {/* Leader Line to Callout Box */}
                    <line x1="-8" y1="0" x2="-24" y2="0" stroke="var(--color-sun)" strokeWidth="1" />
                    
                    {/* Callout Box placed to the LEFT */}
                    <rect x="-185" y="-18" width="160" height="36" rx="4" fill="var(--color-surface)" stroke="var(--color-sun)" strokeWidth="1.2" opacity="0.95" />
                    <text x="-177" y="-3" fill="var(--color-sun)" fontFamily="var(--font-mono)" fontSize="10" fontWeight="bold">
                      [!] AIS SILENCE (07:50)
                    </text>
                    <text x="-177" y="11" fill="var(--color-fog)" fontFamily="var(--font-mono)" fontSize="8.5">
                      Transponder Cut Off · Last Fix
                    </text>
                  </g>
                );
              }

              // 3. False / Spoofed Location: Top-centered callout box (above marker, zero clash with SAR echo to right)
              if (item.type === "spoofed") {
                return (
                  <g
                    key={item.id}
                    transform={`translate(${x}, ${y})`}
                    onClick={() => setSelectedEventId(item.id)}
                    className="cursor-pointer"
                  >
                    {/* Red Hexagon Marker */}
                    <polygon
                      points="0,-10 9,-5 9,5 0,10 -9,5 -9,-5"
                      fill="var(--color-flare)"
                      stroke="var(--color-white)"
                      strokeWidth="1.5"
                    />

                    {/* Leader Line Upwards */}
                    <line x1="0" y1="-10" x2="0" y2="-20" stroke="var(--color-flare)" strokeWidth="1" />

                    {/* Callout Box placed ABOVE */}
                    <rect x="-95" y="-56" width="190" height="35" rx="4" fill="var(--color-surface)" stroke="var(--color-flare)" strokeWidth="1.2" opacity="0.95" />
                    <text x="0" y="-41" fill="var(--color-flare)" fontFamily="var(--font-mono)" fontSize="10" fontWeight="bold" textAnchor="middle">
                      [!] SPOOFED AIS LOCATION (08:05)
                    </text>
                    <text x="0" y="-27" fill="var(--color-fog)" fontFamily="var(--font-mono)" fontSize="8.5" textAnchor="middle">
                      Fabricated Coord · +31.4 kn False Jump
                    </text>
                  </g>
                );
              }

              // 4. SAR Radar Echo: Right-placed callout box with ample breathing room
              if (item.type === "sar") {
                return (
                  <g
                    key={item.id}
                    transform={`translate(${x}, ${y})`}
                    onClick={() => setSelectedEventId(item.id)}
                    className="cursor-pointer"
                  >
                    {/* Glowing Radar Target Crosshairs */}
                    <circle cx="0" cy="0" r="18" fill="url(#sarHitGlow)" />
                    <circle cx="0" cy="0" r="8" fill="none" stroke="var(--color-white)" strokeWidth="2" />
                    <circle cx="0" cy="0" r="3" fill="var(--color-flare)" />
                    <line x1="-12" y1="0" x2="12" y2="0" stroke="var(--color-white)" strokeWidth="1.5" />
                    <line x1="0" y1="-12" x2="0" y2="12" stroke="var(--color-white)" strokeWidth="1.5" />

                    {/* Leader Line to the Right */}
                    <line x1="12" y1="0" x2="22" y2="0" stroke="var(--color-tide)" strokeWidth="1" />

                    {/* Callout Box placed to the RIGHT */}
                    <rect x="22" y="-18" width="185" height="36" rx="4" fill="var(--color-surface)" stroke="var(--color-tide)" strokeWidth="1.2" opacity="0.95" />
                    <text x="30" y="-3" fill="var(--color-white)" fontFamily="var(--font-display)" fontSize="11" fontWeight="bold">
                      SAR RADAR ECHO (7.9m)
                    </text>
                    <text x="30" y="11" fill="var(--color-tide)" fontFamily="var(--font-mono)" fontSize="8.5" fontWeight="bold">
                      Dark Contact Intercepted · S1-CSAR
                    </text>
                  </g>
                );
              }

              return null;
            })}
          </svg>

          <div className="coordinate-readout">
            <Micro>
              {isPragati
                ? "SAR-GAP-MATCH: 19.0000°N / 72.7181°E (7.9m residual error from dead-reckoning)"
                : `${currentShip?.name}: ${currentShip?.current_position.lat.toFixed(4)}°N / ${currentShip?.current_position.lon.toFixed(4)}°E`}
            </Micro>
          </div>
        </div>

        {/* CHRONOLOGICAL HISTORICAL TELEMETRY LOG (BREADCRUMBS) */}
        <div className="tactical-panel mt-3">
          <div className="flex justify-between items-center border-b border-line pb-2 mb-2">
            <Micro className="text-tide">HISTORICAL TRACK & ANOMALY LOG · {currentShip?.name}</Micro>
            <span className="font-mono text-micro text-fog">Click event to inspect on radar</span>
          </div>

          <div className="space-y-2">
            {breadcrumbHistory.map((item) => {
              const isSelected = selectedEventId === item.id;
              const isAlert = item.type === "gap" || item.type === "spoofed";
              const isSar = item.type === "sar";

              return (
                <div
                  key={item.id}
                  onClick={() => setSelectedEventId(item.id)}
                  className={`p-2.5 rounded border transition-all cursor-pointer font-mono text-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 ${
                    isSar
                      ? "bg-tide/10 border-tide"
                      : isAlert
                      ? "bg-flare/10 border-flare"
                      : isSelected
                      ? "bg-surface border-white"
                      : "bg-surface border-line hover:border-fog"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <span className="font-bold text-white whitespace-nowrap">{item.time}</span>
                    <span
                      className={`px-2 py-0.5 rounded text-micro font-bold uppercase ${
                        isSar
                          ? "bg-tide text-night font-bold"
                          : item.type === "spoofed"
                          ? "badge-flare"
                          : item.type === "gap"
                          ? "badge-sun"
                          : "bg-surface border border-line text-fog"
                      }`}
                    >
                      {item.type}
                    </span>
                    <span className="font-display font-semibold text-white">{item.label}</span>
                  </div>

                  <div className="flex items-center gap-4 text-micro text-fog">
                    <span>
                      Coords: <b className="text-white">{item.lat.toFixed(3)}°N, {item.lon.toFixed(3)}°E</b>
                    </span>
                    <span>
                      SOG: <b className={item.type === "spoofed" ? "text-flare font-bold" : "text-white"}>{item.sog}</b>
                    </span>
                    <span>
                      COG: <b className="text-white">{item.cog}</b>
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* RADAR TARGET METRICS */}
        <div className="tactical-panel mt-3">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="stat-box">
              <span className="text-micro font-mono text-fog block">VESSEL TARGET</span>
              <span className="font-mono text-base font-bold text-white">{currentShip?.name}</span>
            </div>
            <div className="stat-box">
              <span className="text-micro font-mono text-fog block">AIS BLACKOUT</span>
              <span className={`font-mono text-base font-bold ${isPragati ? "text-flare" : "text-tide"}`}>
                {isPragati ? "0.5 Hours Silence" : "None (0.0h)"}
              </span>
            </div>
            <div className="stat-box">
              <span className="text-micro font-mono text-fog block">CORRIDOR LIMIT</span>
              <span className="font-mono text-base font-bold text-white">±{primaryMatch?.corridor_radius_m.toFixed(0) || 1360} m</span>
            </div>
            <div className="stat-box">
              <span className="text-micro font-mono text-fog block">SAR RESIDUAL OFFSET</span>
              <span className={`font-mono text-base font-bold ${isPragati ? "text-flare" : "text-fog"}`}>
                {isPragati ? `${primaryMatch?.detection_distance_m.toFixed(1) || 7.9} m (${corridorBudgetUsed}%)` : "N/A"}
              </span>
            </div>
          </div>
        </div>

        {/* OBSERVATION WINDOW PLANNER TABLE */}
        {rankedWindows.length > 0 && (
          <div className="tactical-panel mt-3">
            <div className="flex justify-between items-center border-b border-line pb-2 mb-2">
              <Micro className="text-tide">RECONNAISSANCE PASS SCHEDULING (SENTINEL-1 & RADARSAT)</Micro>
              <span className="font-mono text-micro text-fog">{rankedWindows.length} Windows Ranked</span>
            </div>

            <table className="tactical-table">
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Pass Window (UTC)</th>
                  <th>Separation Score</th>
                  <th>Region A</th>
                  <th>Region B</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {rankedWindows.map((win, idx) => {
                  const isTop = idx === 0;
                  const isTasked = taskedWindow === win.time;
                  const regA = win.predicted_regions?.find((r) => r.hypothesis_id === "H-A");
                  const regB = win.predicted_regions?.find((r) => r.hypothesis_id === "H-B");

                  return (
                    <tr key={idx} className={isTasked ? "bg-tide/10" : ""}>
                      <td className="font-bold text-white">
                        {isTop ? <span className="text-tide">★ 01</span> : `0${idx + 1}`}
                      </td>
                      <td className="font-bold text-white whitespace-nowrap">
                        {win.time.replace("T", " ").replace("Z", "")}
                      </td>
                      <td>
                        <div className="flex items-center gap-2">
                          <div className="w-20 bg-surface h-2 rounded-full overflow-hidden border border-line">
                            <div
                              className={`h-full ${win.separation_score > 0.5 ? "bg-tide" : "bg-sun"}`}
                              style={{ width: `${Math.round(win.separation_score * 100)}%` }}
                            />
                          </div>
                          <span className="font-bold text-white">{win.separation_score.toFixed(3)}</span>
                        </div>
                      </td>
                      <td className="text-fog">
                        {regA ? `${regA.center.lat.toFixed(2)}°N, ${regA.center.lon.toFixed(2)}°E` : "—"}
                      </td>
                      <td className="text-fog">
                        {regB ? `${regB.center.lat.toFixed(2)}°N, ${regB.center.lon.toFixed(2)}°E` : "—"}
                      </td>
                      <td>
                        <button
                          type="button"
                          onClick={() => setTaskedWindow(win.time)}
                          className={`px-2.5 py-1 font-mono text-micro rounded border cursor-pointer transition-all ${
                            isTasked
                              ? "bg-tide text-night font-bold border-tide"
                              : "bg-surface border-line text-white hover:border-tide"
                          }`}
                        >
                          {isTasked ? "TASKED" : "TASK"}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* AIS TRUST & SAR RADAR FOOTPRINT CROSS-VERIFICATION */}
        {aisTrust && (
          <div className="tactical-panel mt-3">
            <div className="flex justify-between items-center border-b border-line pb-2 mb-2">
              <div className="flex items-center gap-2">
                <span className="size-2 rounded-full bg-tide" />
                <Micro className="text-tide">SPACEBORNE SAR RADAR FOOTPRINT & AIS TRUST AUDIT</Micro>
              </div>
              <div className="flex gap-2 font-mono text-micro">
                <span className="px-2 py-0.5 rounded bg-kelp/20 border border-kelp/30 text-kelp font-bold">
                  {aisTrust.matches?.length || 0} Radar Matches
                </span>
                <span className="px-2 py-0.5 rounded bg-flare/20 border border-flare/30 text-flare font-bold">
                  {aisTrust.unmatched_sar_detections?.length || 0} Dark Radar Contacts
                </span>
                <span className="px-2 py-0.5 rounded bg-sun/20 border border-sun/30 text-sun font-bold">
                  {aisTrust.ais_positions_without_sar_match_inside_scene?.length || 0} Ghost Transponders
                </span>
              </div>
            </div>

            <table className="tactical-table">
              <thead>
                <tr>
                  <th>Target Type</th>
                  <th>Detection ID / MMSI</th>
                  <th>Spatial Offset</th>
                  <th>Time Delta</th>
                  <th>Correlation Status</th>
                </tr>
              </thead>
              <tbody>
                {aisTrust.matches?.map((m) => (
                  <tr key={m.detection_id}>
                    <td>
                      <span className="flex items-center gap-2">
                        <span className="size-2 rounded-full bg-kelp" />
                        <span className="font-bold text-white font-mono">RADAR + AIS</span>
                      </span>
                    </td>
                    <td className="text-white font-mono">{m.detection_id} ↔ {m.mmsi}</td>
                    <td className="text-kelp font-mono">{m.distance_m.toFixed(1)} m</td>
                    <td className="text-fog font-mono">{m.time_delta_seconds}s</td>
                    <td>
                      <span className="px-2 py-0.5 rounded text-micro bg-kelp/20 text-kelp font-mono border border-kelp/30 uppercase">
                        VERIFIED CONTACT
                      </span>
                    </td>
                  </tr>
                ))}
                {aisTrust.unmatched_sar_detections?.map((d) => (
                  <tr key={d.detection_id}>
                    <td>
                      <span className="flex items-center gap-2">
                        <span className="size-2 rounded-full bg-flare animate-pulse" />
                        <span className="font-bold text-flare font-mono">DARK TARGET</span>
                      </span>
                    </td>
                    <td className="text-white font-mono">{d.detection_id} ({d.lat.toFixed(3)}°N, {d.lon.toFixed(3)}°E)</td>
                    <td className="text-flare font-mono">No Transponder</td>
                    <td className="text-fog font-mono">—</td>
                    <td>
                      <span className="px-2 py-0.5 rounded text-micro bg-flare/20 text-flare font-mono border border-flare/30 uppercase">
                        RADAR ECHO ONLY (DARK SHIP)
                      </span>
                    </td>
                  </tr>
                ))}
                {aisTrust.ais_positions_without_sar_match_inside_scene?.map((a) => (
                  <tr key={a.mmsi}>
                    <td>
                      <span className="flex items-center gap-2">
                        <span className="size-2 rounded-full bg-sun" />
                        <span className="font-bold text-sun font-mono">GHOST AIS</span>
                      </span>
                    </td>
                    <td className="text-white font-mono">{a.mmsi}</td>
                    <td className="text-sun font-mono">No Radar Reflection</td>
                    <td className="text-fog font-mono">In-Scene</td>
                    <td>
                      <span className="px-2 py-0.5 rounded text-micro bg-sun/20 text-sun font-mono border border-sun/30 uppercase">
                        UNVERIFIED TRANSPONDER
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* COMMIT 7: Jurisdictional Boundary Escape & Coast Guard Intercept Feasibility */}
        {escapeIntercept && (
          <div className="tactical-panel mt-3 border-l-2 border-l-flare">
            <div className="flex justify-between items-center border-b border-line pb-2 mb-2">
              <div className="flex items-center gap-2">
                <span className="size-2 rounded-full bg-flare" />
                <Micro className="text-flare">JURISDICTIONAL BOUNDARY ESCAPE & INTERCEPT FEASIBILITY</Micro>
              </div>
              <span className="font-mono text-micro px-2 py-0.5 rounded bg-flare/20 text-flare font-bold border border-flare/30">
                {escapeIntercept.jurisdiction_status === "projected_exit_found"
                  ? "EEZ ESCAPE TRAJECTORY DETECTED"
                  : "WITHIN TERRITORIAL JURISDICTION"}
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 font-mono text-xs">
              <div className="p-2.5 bg-surface border border-line rounded">
                <span className="text-fog text-micro block">PROJECTED BOUNDARY EXIT</span>
                <div className="mt-1 flex items-baseline gap-2">
                  <span className="text-flare text-base font-bold">
                    +{escapeIntercept.projected_boundary_exit?.eta_hours.toFixed(2)}h
                  </span>
                  <span className="text-white text-xs">
                    ({escapeIntercept.projected_boundary_exit?.time
                      ? new Date(escapeIntercept.projected_boundary_exit.time).toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                        })
                      : "09:08"}{" "}
                    UTC)
                  </span>
                </div>
                <p className="mt-1 text-fog text-micro">
                  Exit coordinates: {escapeIntercept.projected_boundary_exit?.position.lat.toFixed(3)}°N,{" "}
                  {escapeIntercept.projected_boundary_exit?.position.lon.toFixed(3)}°E
                </p>
              </div>

              <div className="p-2.5 bg-surface border border-line rounded">
                <span className="text-fog text-micro block">INTERCEPT PATROL ASSET</span>
                <div className="mt-1 flex items-baseline gap-2">
                  <span className="text-tide text-base font-bold">
                    {escapeIntercept.interception_estimate?.base || "ICGS Mumbai Base"}
                  </span>
                  <span className="text-fog text-xs">(30 kn fast interceptor)</span>
                </div>
                <p className="mt-1 text-fog text-micro">
                  Patrol ETA:{" "}
                  {escapeIntercept.interception_estimate
                    ? (escapeIntercept.interception_estimate.patrol_eta_hours * 60).toFixed(0)
                    : "35"}{" "}
                  min · Intercept at {escapeIntercept.interception_estimate?.position.lat.toFixed(3)}°N,{" "}
                  {escapeIntercept.interception_estimate?.position.lon.toFixed(3)}°E
                </p>
              </div>

              <div className="p-2.5 bg-surface border border-line rounded">
                <span className="text-fog text-micro block">TACTICAL SAFETY MARGIN</span>
                <div className="mt-1 flex items-baseline gap-2">
                  <span className="text-sun text-base font-bold">
                    +{escapeIntercept.interception_estimate
                      ? (escapeIntercept.interception_estimate.time_margin_hours * 60).toFixed(1)
                      : "10.2"}{" "}
                    min
                  </span>
                  <span className="text-tide text-xs font-bold">INTERCEPT ACHIEVABLE</span>
                </div>
                <p className="mt-1 text-fog text-micro">
                  Interdiction viable before suspect enters international waters (rendezvous{" "}
                  {escapeIntercept.interception_estimate?.time
                    ? new Date(escapeIntercept.interception_estimate.time).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })
                    : "08:45"}{" "}
                  UTC)
                </p>
              </div>
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
              <Micro className="text-tide">Target Selection</Micro>
              <p className="mt-2 font-display text-xl font-medium">Tracked Fleet ({ships.length})</p>
            </div>
            <span className="grid size-10 place-items-center border border-tide/30 text-tide">
              <Icon name="radar" className="size-5" />
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
                      {ship.code} · State: <b className={ship.mmsi === "IND-7319" ? "text-flare" : "text-white"}>{ship.state}</b>
                    </span>
                  </span>
                  <span className="risk-number">{ship.risk.toFixed(2)}</span>
                </Action>
              );
            })}
          </div>
        </section>

        {/* Radar Specification Ledger */}
        <section className="ledger">
          <div className="ledger-head">
            <div>
              <Micro className="text-tide">Sensor Specification</Micro>
              <p className="mt-2 font-display text-xl font-medium">Sentinel-1 C-SAR</p>
            </div>
            <span className="grid size-10 place-items-center border border-tide/30 text-tide">
              <Icon name="satellite" className="size-5" />
            </span>
          </div>

          <div className="mt-4 space-y-3 font-mono text-xs">
            <div className="flex justify-between pb-2 border-b border-line">
              <span className="text-fog">Mode:</span>
              <span className="text-white">IW Dual-Pol</span>
            </div>
            <div className="flex justify-between pb-2 border-b border-line">
              <span className="text-fog">Incidence Angle:</span>
              <span className="text-white font-bold">34.2°</span>
            </div>
            <div className="flex justify-between pb-2 border-b border-line">
              <span className="text-fog">Spatial Resolution:</span>
              <span className="text-white">10m Ground Range</span>
            </div>
            <div className="flex justify-between pb-2 border-b border-line">
              <span className="text-fog">Corridor Budget:</span>
              <span className="text-flare font-bold">{corridorBudgetUsed}% Used (7.9m)</span>
            </div>
          </div>

          {/* Stamp */}
          <div className="attribution-stamp">
            <div className={`stamp-ring ${isPragati ? "border-flare text-flare" : "border-fog text-fog"}`}>
              <span>{isPragati ? "99" : "00"}</span>
              <small>%</small>
            </div>
            <div>
              <Micro className={isPragati ? "text-flare" : "text-fog"}>Radar Correlation</Micro>
              <p className="mt-1 text-xs text-fog">
                {isPragati
                  ? "Dark vessel dead-reckoning kinematics match Sentinel-1 SAR contact within 7.9m."
                  : "Continuous AIS broadcast. No dark vessel SAR correlation required."}
              </p>
            </div>
          </div>
        </section>

        {/* Intercept Card (Commit 7) */}
        {escapeIntercept?.interception_estimate && (
          <section className="eco-card border-l-2 border-l-sun">
            <div className="eco-icon">
              <Icon name="shield" className="size-6 text-sun" />
            </div>
            <div className="min-w-0 flex-1">
              <Micro className="text-sun">Intercept Feasibility</Micro>
              <p className="mt-1 font-mono text-sm font-bold text-white">
                {escapeIntercept.interception_estimate.base}
              </p>
              <p className="text-xs text-fog font-mono mt-0.5">
                Margin:{" "}
                <b className="text-sun">
                  +{(escapeIntercept.interception_estimate.time_margin_hours * 60).toFixed(0)} min
                </b>{" "}
                before EEZ exit
              </p>
            </div>
          </section>
        )}

        {/* Tasking Card */}
        {recommendedWindow && (
          <section className="eco-card">
            <div className="eco-icon"><Icon name="satellite" className="size-6 text-tide" /></div>
            <div className="min-w-0 flex-1">
              <Micro className="text-tide">Optimal Recon Window</Micro>
              <p className="mt-1 font-mono text-sm font-bold text-white">
                {recommendedWindow.time.replace("T", " ").replace("Z", "")} UTC
              </p>
              <p className="text-xs text-fog font-mono mt-0.5">Separation: <b className="text-tide">{recommendedWindow.separation_score.toFixed(3)}</b></p>
            </div>
          </section>
        )}
      </aside>

      {/* FOOTER */}
      <section className="case-footer">
        <span><Micro className="text-fog">Target</Micro><b>{currentShip?.name}</b></span>
        <span><Micro className="text-fog">Corridor</Micro><b>±1360 M</b></span>
        <span><Micro className="text-fog">SAR Offset</Micro><b className={isPragati ? "text-flare" : "text-fog"}>{isPragati ? "7.9 M" : "NOMINAL"}</b></span>
        <span>
          <Micro className="text-fog">EEZ Intercept</Micro>
          <b className="text-sun">
            {escapeIntercept?.interception_estimate ? "+10.2M MARGIN" : "VERIFIED"}
          </b>
        </span>
        <span className="case-footer-note">
          Kinematic dead-reckoning correlated with Sentinel-1 Level-1 GRD. Multi-ship AIS breadcrumb reconstruction & Coast Guard escape intercept feasibility.
        </span>
      </section>
    </div>
  );
}
