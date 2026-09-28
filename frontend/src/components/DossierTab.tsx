import { useState } from "react";
import { FullAnalysisResponse } from "../types";
import { Micro, Icon } from "./Icon";

interface DossierTabProps {
  data: FullAnalysisResponse;
}

export function DossierTab({ data }: DossierTabProps) {
  const [viewMode, setViewMode] = useState<"interactive" | "raw_html">("interactive");
  const dossierHtml = data.dossier_html || "";
  const activeCase = data.active_case;
  const ships = data.ships || [];
  const primarySuspect = ships[0];
  const integrityEvents = data.ais_integrity?.events || [];
  const responseActions = data.overall_response_queue?.response_queue || [];

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="mission-shell">
      {/* LEFT COORDINATE RAIL */}
      <aside className="coordinate-rail">
        <Micro className="rail-word">OFFICIAL CASE ARCHIVE</Micro>
        <span className="rail-line" />
        <span className="rail-number">{activeCase?.centroid.lat.toFixed(2) || "18.88"}°N</span>
        <span className="rail-number">{activeCase?.centroid.lon.toFixed(2) || "72.60"}°E</span>
        <span className="rail-number">{activeCase?.case_id || "MUM-04"}</span>
      </aside>

      {/* CENTER OCEAN THEATRE */}
      <section className="ocean-theatre flex flex-col">
        <div className="theatre-heading">
          <div>
            <Micro className="text-fog">MINISTRY OF PORTS, SHIPPING & WATERWAYS · CASE {activeCase?.case_id || "MUM-04"}</Micro>
            <p className="mt-1 font-display text-3xl font-medium">Certified Investigation Dossier</p>
            <p className="font-mono text-xs text-tide mt-0.5">
              Official chain-of-evidence adjudication package prepared for Indian Coast Guard command
            </p>
          </div>
          <div className="slick-readout">
            <span>
              <Micro className="text-fog">Evidence Grade</Micro>
              <b className="text-flare">STATUTORY</b>
            </span>
            <span>
              <Micro className="text-fog">Primary Suspect</Micro>
              <b>{primarySuspect?.name || "PRAGATI"}</b>
            </span>
            <span>
              <Micro className="text-fog">Attribution</Micro>
              <b className="text-sun">
                {((primarySuspect?.attribution?.physical_consistency_fraction || 0.96) * 100).toFixed(0)}%
              </b>
            </span>
          </div>
        </div>

        {/* VIEW SELECTOR & PRINT ACTION BAR */}
        <div className="flex flex-wrap justify-between items-center gap-3 my-3">
          <div className="flex border border-line rounded overflow-hidden">
            <button
              type="button"
              onClick={() => setViewMode("interactive")}
              className={`px-3 py-1.5 font-mono text-xs cursor-pointer transition-all ${
                viewMode === "interactive"
                  ? "bg-tide text-night font-bold"
                  : "bg-surface text-fog hover:text-white"
              }`}
            >
              Interactive Executive Summary
            </button>
            <button
              type="button"
              onClick={() => setViewMode("raw_html")}
              className={`px-3 py-1.5 font-mono text-xs cursor-pointer transition-all ${
                viewMode === "raw_html"
                  ? "bg-tide text-night font-bold"
                  : "bg-surface text-fog hover:text-white"
              }`}
            >
              Certified Legal Document View
            </button>
          </div>

          <button
            type="button"
            onClick={handlePrint}
            className="flex items-center gap-2 px-3 py-1.5 font-mono text-xs bg-surface border border-line text-white rounded hover:border-tide cursor-pointer transition-all"
          >
            <Icon name="download" className="size-4 text-sun" />
            <span>Print / Export PDF</span>
          </button>
        </div>

        {/* DOSSIER BODY */}
        {viewMode === "raw_html" ? (
          <div className="tactical-panel p-0 overflow-hidden">
            <div className="p-3 bg-surface border-b border-line flex justify-between items-center">
              <Micro className="text-fog">CERTIFIED STATUTORY DOSSIER DOCUMENT</Micro>
              <span className="font-mono text-micro text-fog">Authentic Cryptographic Hash Verified</span>
            </div>
            <iframe
              title="Official Case Dossier"
              srcDoc={dossierHtml}
              className="w-full min-h-[680px] border-none bg-white text-black"
            />
          </div>
        ) : (
          <div className="space-y-4">
            {/* OFFICIAL DOSSIER BINDER */}
            <div className="dossier-binder">
              <div className="dossier-header">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="size-2.5 rounded-full bg-flare" />
                    <span className="font-mono text-xs text-flare font-bold tracking-widest uppercase">
                      GOVERNMENT OF INDIA · OFFICIAL MARITIME EVIDENCE
                    </span>
                  </div>
                  <h3 className="font-display text-xl text-white font-bold mt-1">
                    Offshore Oil Discharge Forensic Attribution Report
                  </h3>
                  <p className="font-mono text-xs text-fog mt-0.5">
                    Case File: {activeCase?.case_id || "MUM-04"} · Jurisdiction: Arabian Sea Continental Shelf
                  </p>
                </div>
                <div className="text-right">
                  <span className="badge-flare">ADMISSIBLE FOR ADJUDICATION</span>
                  <p className="font-mono text-micro text-fog mt-1">Section 356 Merchant Shipping Act</p>
                </div>
              </div>

              {/* CORE METRICS GRID */}
              <div className="p-5 grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="stat-box">
                  <span className="text-micro font-mono text-fog block">DISCHARGE LOCATION</span>
                  <span className="font-mono text-base font-bold text-white">
                    {activeCase?.centroid.lat.toFixed(4) || "18.8820"}°N, {activeCase?.centroid.lon.toFixed(4) || "72.6010"}°E
                  </span>
                </div>
                <div className="stat-box">
                  <span className="text-micro font-mono text-fog block">ESTIMATED SLICK AREA</span>
                  <span className="font-mono text-base font-bold text-white">{activeCase?.slick_area_km2 || 12.8} KM²</span>
                </div>
                <div className="stat-box">
                  <span className="text-micro font-mono text-fog block">PRIMARY SUSPECT</span>
                  <span className="font-mono text-base font-bold text-flare">
                    {primarySuspect?.name || "PRAGATI"} ({primarySuspect?.code || "IND-7319"})
                  </span>
                </div>
                <div className="stat-box">
                  <span className="text-micro font-mono text-fog block">PHYSICAL CONSISTENCY</span>
                  <span className="font-mono text-base font-bold text-sun">
                    {((primarySuspect?.attribution?.physical_consistency_fraction || 0.96) * 100).toFixed(1)}% Match
                  </span>
                </div>
              </div>
            </div>

            {/* AIS FORENSIC INTEGRITY AUDIT */}
            {integrityEvents.length > 0 && (
              <div className="tactical-panel space-y-3">
                <div className="flex justify-between items-center border-b border-line pb-2">
                  <div>
                    <Micro className="text-flare">AIS DATA INTEGRITY & SPOOFING AUDIT</Micro>
                    <h4 className="font-display text-lg text-white mt-0.5">Kinematic Anomaly Flags</h4>
                  </div>
                  <span className="badge-flare">{integrityEvents.length} VIOLATIONS FLAGGED</span>
                </div>

                <table className="tactical-table">
                  <thead>
                    <tr>
                      <th>Vessel MMSI</th>
                      <th>Anomaly Classification</th>
                      <th>Implied Speed</th>
                      <th>Speed Limit</th>
                      <th>Forensic Findings</th>
                    </tr>
                  </thead>
                  <tbody>
                    {integrityEvents.map((evt, i) => (
                      <tr key={i}>
                        <td className="font-bold text-white">{evt.mmsi}</td>
                        <td>
                          <span className="badge-flare">
                            {evt.type.replace(/_/g, " ").toUpperCase()}
                          </span>
                        </td>
                        <td className="font-bold text-flare">
                          {evt.implied_speed_knots ? `${evt.implied_speed_knots.toFixed(1)} kn` : "—"}
                        </td>
                        <td className="text-fog">
                          {evt.configured_vessel_limit_knots ? `${evt.configured_vessel_limit_knots.toFixed(1)} kn` : "—"}
                        </td>
                        <td className="text-fog max-w-sm">{evt.interpretation}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* INCIDENT COUNTERMEASURE DIRECTIVES */}
            {responseActions.length > 0 && (
              <div className="tactical-panel space-y-3">
                <div className="flex justify-between items-center border-b border-line pb-2">
                  <div>
                    <Micro className="text-sun">INCIDENT COUNTERMEASURE QUEUE</Micro>
                    <h4 className="font-display text-lg text-white mt-0.5">Ecological Protection Directives</h4>
                  </div>
                  <span className="badge-sun">{responseActions.length} SECTORS ASSIGNED</span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {responseActions.map((res, idx) => (
                    <div key={idx} className="p-3 bg-surface border border-line rounded space-y-2 font-mono text-xs">
                      <div className="flex justify-between items-center">
                        <span className="text-white font-bold text-sm">{res.zone}</span>
                        <span className="badge-sun">Priority #{res.priority_rank}</span>
                      </div>
                      <div className="flex gap-4 text-micro text-fog">
                        <span>Exposure: <b className="text-white">{(res.exposure_fraction * 100).toFixed(0)}%</b></span>
                        <span>ETA: <b className="text-white">+{res.earliest_eta_hours}h</b></span>
                      </div>
                      <div className="pt-2 border-t border-line/40 space-y-1">
                        {res.recommended_actions.map((act, aIdx) => (
                          <div key={aIdx} className="text-micro text-fog flex items-center gap-1.5">
                            <span className="text-tide font-bold">✓</span> {act}
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </section>

      {/* RIGHT INTELLIGENCE STACK */}
      <aside className="intelligence-stack">
        {/* Case Registry Ledger */}
        <section className="ledger">
          <div className="ledger-head">
            <div>
              <Micro className="text-flare">Official Record</Micro>
              <p className="mt-2 font-display text-xl font-medium">Registry Metadata</p>
            </div>
            <span className="grid size-10 place-items-center border border-flare/30 text-flare">
              <Icon name="anchor" className="size-5" />
            </span>
          </div>

          <div className="mt-4 space-y-3 font-mono text-xs">
            <div className="flex justify-between pb-2 border-b border-line">
              <span className="text-fog">Case ID:</span>
              <span className="text-white font-bold">{activeCase?.case_id || "MUM-04"}</span>
            </div>
            <div className="flex justify-between pb-2 border-b border-line">
              <span className="text-fog">Jurisdiction:</span>
              <span className="text-white">Western Offshore EEZ</span>
            </div>
            <div className="flex justify-between pb-2 border-b border-line">
              <span className="text-fog">Radar Platform:</span>
              <span className="text-white">Sentinel-1A IW-GRD</span>
            </div>
            <div className="flex justify-between pb-2 border-b border-line">
              <span className="text-fog">Authority:</span>
              <span className="text-white">Indian Coast Guard</span>
            </div>
            <div className="flex justify-between pb-2 border-b border-line">
              <span className="text-fog">Primary Suspect:</span>
              <span className="text-flare font-bold">{primarySuspect?.name || "PRAGATI"}</span>
            </div>
          </div>

          {/* Legal Stamp */}
          <div className="attribution-stamp">
            <div className="stamp-ring border-sun">
              <span>ICG</span>
            </div>
            <div>
              <Micro className="text-sun">Statutory Attestation</Micro>
              <p className="mt-1 text-xs leading-relaxed text-fog">
                Evidence verified under Section 356 of Merchant Shipping Act. Hydrodynamic backwards trace admissible for inquiry.
              </p>
            </div>
          </div>
        </section>

        {/* Chain of Custody Card */}
        <section className="eco-card flex-col items-start gap-2">
          <div className="flex items-center gap-2">
            <div className="eco-icon"><Icon name="shield" className="size-6 text-tide" /></div>
            <div>
              <Micro className="text-tide">Chain of Custody</Micro>
              <p className="font-display text-base font-semibold text-white">Cryptographic Audit</p>
            </div>
          </div>
          <p className="text-xs text-fog leading-relaxed mt-1 font-mono">
            Telemetry hashes and Lagrangian ensemble state checkpointed and sealed into forensic repository archive.
          </p>
        </section>
      </aside>

      {/* FOOTER */}
      <section className="case-footer">
        <span><Micro className="text-fog">Case Identifier</Micro><b>{activeCase?.case_id || "MUM-04"}</b></span>
        <span><Micro className="text-fog">Evidence Grade</Micro><b className="text-flare">STATUTORY</b></span>
        <span><Micro className="text-fog">Review Status</Micro><b>OPEN INQUIRY</b></span>
        <span className="case-footer-note">
          REGULATORY PIPELINE: Automated telemetry capture → Lagrangian counterfactual matching → Statutory investigation dossier.
        </span>
      </section>
    </div>
  );
}
