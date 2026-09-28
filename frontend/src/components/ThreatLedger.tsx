import { ShipData, TemporalRiskResult, ContextualBehaviorResult, ContextualMetricSignal } from "../types";
import { Action, Icon, Micro } from "./Icon";

interface ThreatLedgerProps {
  ships: ShipData[];
  selectedMmsi: string;
  onSelectMmsi: (mmsi: string) => void;
  temporalRisk?: TemporalRiskResult;
  contextualBehavior?: ContextualBehaviorResult;
}

export function ThreatLedger({ ships, selectedMmsi, onSelectMmsi, temporalRisk, contextualBehavior }: ThreatLedgerProps) {
  const selectedShip = ships.find(s => s.mmsi === selectedMmsi) || ships[0];
  const candidate = selectedShip?.attribution;
  const matchPercent = candidate ? Math.round(candidate.physical_consistency_fraction * 100) : 0;
  const matchRuns = candidate ? candidate.compatible_simulations : 0;
  const totalRuns = candidate ? candidate.total_simulations : 80;

  // Selected ship integrity flags (Commit 5)
  const integrityFlags = selectedShip?.integrity_flags || [];

  // Selected ship temporal risk (Commit 5)
  const shipTemporalRisk = temporalRisk?.vessels?.find(v => v.mmsi === selectedShip?.mmsi);

  // Selected ship contextual behavior (Commit 6)
  const shipContextualObs = contextualBehavior?.observations?.find(o => o.mmsi === selectedShip?.mmsi);

  return (
    <section className="ledger">
      <div className="ledger-head">
        <div>
          <Micro className="text-flare">Threat ledger</Micro>
          <p className="mt-2 font-display text-xl font-medium">Suspect Vessels ({ships.length})</p>
        </div>
        <span className="grid size-10 place-items-center border border-flare/30 text-flare">
          <Icon name="crosshair" className="size-5" />
        </span>
      </div>

      <div className="mt-5 space-y-2">
        {ships.map((ship, index) => {
          const isActive = selectedMmsi === ship.mmsi;
          const flags = ship.integrity_flags || [];
          const hasIntegrityViolation = flags.length > 0;

          return (
            <Action
              key={ship.mmsi}
              active={isActive}
              onClick={() => onSelectMmsi(ship.mmsi)}
              className={`ledger-target w-full ${isActive ? "is-active" : ""}`}
            >
              <span className="target-index">0{index + 1}</span>
              <span className="min-w-0 flex-1 text-left">
                <span className="block truncate font-display text-sm font-semibold tracking-wide flex items-center justify-between">
                  <span>{ship.name}</span>
                  <span className="font-mono text-micro text-fog uppercase">{ship.vessel_type}</span>
                </span>
                <span className="mt-1 flex items-center gap-1.5 flex-wrap font-mono text-micro text-fog">
                  <span>{ship.code}</span>
                  <span>·</span>
                  <span className={isActive ? "text-flare font-bold" : ""}>{ship.state}</span>
                  {hasIntegrityViolation && (
                    <span className="px-1 py-0.2 text-[10px] rounded bg-flare/20 text-flare font-bold border border-flare/30">
                      ⚠️ AIS SPOOF
                    </span>
                  )}
                </span>
              </span>
              <span className="risk-number">{ship.risk.toFixed(2)}</span>
            </Action>
          );
        })}
      </div>

      {/* COMMIT 5: AIS Data Integrity Alert Card */}
      {integrityFlags.length > 0 && (
        <div className="p-3 bg-flare/10 border border-flare/40 rounded space-y-2">
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1.5 font-mono text-xs text-flare font-bold">
              <span>⚠️</span> AIS DATA INTEGRITY VIOLATION
            </span>
            <span className="font-mono text-micro text-flare bg-flare/20 px-1.5 py-0.5 rounded">
              COMMIT 5
            </span>
          </div>
          {integrityFlags.map((flag, idx) => (
            <div key={idx} className="font-mono text-xs text-fog space-y-0.5">
              <div className="text-white font-semibold">
                {flag.type.replace(/_/g, " ").toUpperCase()}
              </div>
              {flag.implied_speed_knots && (
                <div className="text-micro text-flare">
                  Implied speed: <b className="text-white">{flag.implied_speed_knots.toFixed(1)} kn</b> (Max limit: {flag.configured_vessel_limit_knots} kn)
                </div>
              )}
              <div className="text-micro text-fog/80 truncate">
                {flag.interpretation}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* COMMIT 6: Contextual Behavioral Deviations (Z-score anomaly against baseline) */}
      {shipContextualObs && (
        <div className="p-3 bg-sun/10 border border-sun/30 rounded space-y-2">
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1.5 font-mono text-xs text-sun font-bold">
              <span>⚡</span> CONTEXTUAL BEHAVIOR ANOMALIES
            </span>
            <span className="font-mono text-micro text-sun bg-sun/20 px-1.5 py-0.5 rounded font-bold">
              INDEX: {shipContextualObs.contextual_behavior_index.toFixed(3)}
            </span>
          </div>
          <div className="grid grid-cols-2 gap-2 font-mono text-micro">
            {Object.entries(shipContextualObs.metric_signals || {}).map(([metric, rawSig]) => {
              const sig = rawSig as ContextualMetricSignal;
              return (
                <div key={metric} className="p-1.5 bg-surface border border-line rounded">
                  <div className="text-fog uppercase text-[10px] truncate">{metric.replace(/_/g, " ")}</div>
                  <div className="flex justify-between items-baseline mt-0.5">
                    <span className="text-white font-bold">{sig.observed}</span>
                    <span className={sig.severity > 0 ? "text-flare font-bold" : "text-fog"}>
                      Z={sig.standardized_deviation > 0 ? `+${sig.standardized_deviation}` : sig.standardized_deviation}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Attribution analysis stamp for the selected ship */}
      <div className="attribution-stamp">
        <div className={`stamp-ring ${matchPercent > 50 ? "border-flare" : "border-tide"}`}>
          <span>{matchPercent}</span>
          <small>%</small>
        </div>
        <div>
          <Micro className="text-tide">Counterfactual match · {selectedShip?.name}</Micro>
          <p className="mt-2 text-sm leading-relaxed text-fog">
            {matchPercent > 50 ? (
              <>Trajectory is <b className="text-flare">physically consistent</b> with slick MUM-04 across {matchRuns} of {totalRuns} ensemble runs.</>
            ) : (
              <>Trajectory is <b className="text-fog">physically inconsistent</b> with slick MUM-04 ({matchRuns} of {totalRuns} runs fell outside slick envelope).</>
            )}
          </p>
          {shipTemporalRisk && (
            <p className="mt-1.5 font-mono text-micro text-sun">
              Exponential Temporal Risk Index: <b>{shipTemporalRisk.temporal_risk_index.toFixed(3)}</b> (half-life decayed)
            </p>
          )}
        </div>
      </div>

      <div className="ledger-foot">
        <span><Micro className="text-fog">Forecast</Micro><b className="text-flare">+{selectedShip?.drift_forecast.duration_hours || 24}H</b></span>
        <span><Micro className="text-fog">Backtrack</Micro><b className="text-tide">-{selectedShip?.drift_backtrack.duration_hours || 8}H</b></span>
        <span><Micro className="text-fog">Ensemble</Micro><b>{selectedShip?.drift_backtrack.hindcast.run_count || 50} runs</b></span>
      </div>
    </section>
  );
}
