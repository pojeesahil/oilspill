import { ShipData } from "../types";
import { Micro } from "./Icon";

export function EvidenceStream({ ship }: { ship: ShipData }) {
  if (!ship || !ship.vessel_analysis) return null;
  const timeline = ship.vessel_analysis.timeline;

  return (
    <div className="mt-4 border border-line bg-inkwell p-4 flex flex-col gap-4 overflow-x-auto">
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-2">
          <Micro className="text-flare">EVIDENCE STREAM: BEHAVIORAL ACCUMULATION</Micro>
          <span className="font-mono text-micro text-white bg-surface border border-line px-1.5 py-0.5 rounded">
            {ship.name} ({ship.code})
          </span>
        </div>
        <Micro className="text-fog">Decayed Bayesian Risk: <b className="text-flare">{ship.risk.toFixed(2)}</b></Micro>
      </div>

      <div className="flex gap-4 min-w-max pb-2">
        {timeline.map((pt, idx) => {
          // Find the dominant signal
          let maxSignal = "";
          let maxVal = -1;
          for (const [key, val] of Object.entries(pt.signals)) {
            if (val > maxVal) {
              maxVal = val;
              maxSignal = key;
            }
          }

          const isHigh = maxVal > 0.4;
          const dotColor = isHigh ? "bg-flare" : "bg-kelp";
          const timeLabel = new Date(pt.time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

          return (
            <div key={idx} className="flex flex-col items-center gap-2 border-r border-line pr-4 last:border-r-0">
              <Micro className="text-fog">{timeLabel}</Micro>
              <div className={`size-3 rounded-full ${dotColor}`} />
              <div className="text-center">
                <span className="block font-mono text-xs text-white">{maxSignal.replace(/_/g, ' ')}</span>
                <span className={`block font-mono text-xs ${isHigh ? "text-flare font-bold" : "text-tide"}`}>{maxVal.toFixed(2)}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
