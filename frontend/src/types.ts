export interface TimelinePoint {
  time: string;
  lat: number;
  lon: number;
  behavior_score: number;
  signals: {
    speed_deviation: number;
    loitering: number;
    ais_gap: number;
    kinematic: number;
    route_deviation: number;
    course_change: number;
  };
  reasons: string[];
}

export interface VesselAnalysis {
  mmsi: string;
  vessel_type: string;
  operating_context: string;
  behavior_score: number;
  score_meaning: string;
  timeline: TimelinePoint[];
}

export interface TrajectoryPoint {
  time?: string;
  hours?: number;
  lat: number;
  lon: number;
}

export interface OriginPoint {
  lat: number;
  lon: number;
  hours_before: number;
}

export interface HindcastOrigins {
  run_count: number;
  origins: OriginPoint[];
  bounds: {
    lat: [number, number];
    lon: [number, number];
  };
}

export interface DriftForecast {
  forward_track: TrajectoryPoint[];
  duration_hours: number;
  endpoint?: TrajectoryPoint;
}

export interface DriftBacktrack {
  backtrack_track: TrajectoryPoint[];
  duration_hours: number;
  hindcast: HindcastOrigins;
}

export interface DriftAnalysis {
  forward_track: TrajectoryPoint[];
  hindcast_origins: HindcastOrigins;
}

export interface PhysicalConsistencyVector {
  endpoint_count?: number;
  endpoint_envelope_area_m2?: number;
  observed_footprint_area_m2?: number;
  centroid_fraction?: number;
  polygon_support_fraction?: number;
  area_similarity?: number;
  orientation_similarity?: number | null;
  physical_consistency_score?: number;
  score_components_used?: string[];
  interpretation?: string;
}

export interface ReleaseHypothesis {
  release_time: string;
  ensemble_consistency: number;
  simulations: number;
  physical_consistency_vector?: PhysicalConsistencyVector;
}

export interface Candidate {
  mmsi: string;
  physical_consistency_fraction: number;
  physical_consistency_score?: number;
  physical_consistency_vector?: PhysicalConsistencyVector;
  compatible_simulations: number;
  total_simulations: number;
  simulation_endpoints?: {
    lat: number;
    lon: number;
    compatible: boolean;
  }[];
  release_hypotheses: ReleaseHypothesis[];
  sample_trajectory: TrajectoryPoint[];
}

export interface Attribution {
  source_assessment: string;
  threshold_used: number;
  vector_assessment?: string;
  vector_threshold_used?: number;
  candidates: Candidate[];
}

export interface ImpactZone {
  name: string;
  exposure_fraction: number;
  earliest_eta_hours: number;
  consequence_weight: number;
}

export interface ImpactForecast {
  impact_index: number;
  ensemble_runs: number;
  zones: ImpactZone[];
  sample_trajectory: TrajectoryPoint[];
}

export interface SurveillanceItem {
  mmsi: string;
  behavior_index: number;
  spill_opportunity: number;
  potential_impact_index: number;
  data_uncertainty: number;
  incident_proxy: number;
  priority_index: number;
  impact_forecast: ImpactForecast;
}

// === COMMIT 3: Dead Reckoning vs SAR Correlation ===
export interface DeadReckoningMatch {
  mmsi: string;
  detection_id: string;
  hours_since_last_ais: number;
  predicted_position: {
    lat: number;
    lon: number;
  };
  detection_distance_m: number;
  corridor_radius_m: number;
  status: string;
  interpretation: string;
}

export interface DeadReckoningResult {
  matches: DeadReckoningMatch[];
  unmatched_sar_detections?: any[];
  score_meaning: string;
}

// === COMMIT 3: Bayesian Forecast Assimilation ===
export interface ParticleUpdate {
  particle_id: string;
  hypothesis_id: string;
  observation_residual_m: number;
  posterior_weight: number;
}

export interface CorrectedForecastPoint {
  time: string;
  lat: number;
  lon: number;
}

export interface ForecastUpdateResult {
  posterior_hypothesis_weights: Record<string, number>;
  particle_updates: ParticleUpdate[];
  effective_sample_size: number;
  corrected_forecast: CorrectedForecastPoint[];
  interpretation: string;
}

// === COMMIT 4: Observation Window Planner ===
export interface ObservationRegion {
  hypothesis_id: string;
  prior_weight: number;
  center: {
    lat: number;
    lon: number;
  };
  rms_spread_m: number;
}

export interface ObservationWindow {
  time: string;
  separation_score: number;
  predicted_regions: ObservationRegion[];
  interpretation: string;
}

export interface ObservationPlanResult {
  recommended_observation_window?: ObservationWindow;
  ranked_windows: ObservationWindow[];
  score_meaning: string;
}

// === COMMIT 4: Operational Response Queue ===
export interface ResponseActionItem {
  zone: string;
  exposure_fraction: number;
  earliest_eta_hours: number;
  consequence_weight: number;
  priority_rank: number;
  triggered_rules: string[];
  recommended_actions: string[];
  status: string;
}

export interface ResponseQueueResult {
  response_queue: ResponseActionItem[];
  interpretation: string;
}

// === COMMIT 5: AIS Data Integrity Inspection ===
export interface AisIntegrityEvent {
  mmsi: string;
  type: string;
  from_time?: string;
  to_time?: string;
  implied_speed_knots?: number;
  configured_vessel_limit_knots?: number;
  course_change_deg?: number;
  interval_seconds?: number;
  frozen_point_count?: number;
  interpretation: string;
}

export interface AisIntegrityResult {
  events: AisIntegrityEvent[];
  score_meaning: string;
}

// === COMMIT 5: Temporal Risk Decay ===
export interface TemporalRiskEvent {
  time: string;
  type: string;
  severity: number;
  configured_weight: number;
  age_hours: number;
  decay_factor: number;
  current_contribution: number;
}

export interface TemporalRiskVessel {
  mmsi: string;
  as_of_time: string;
  temporal_risk_index: number;
  events: TemporalRiskEvent[];
}

export interface TemporalRiskResult {
  vessels: TemporalRiskVessel[];
  score_meaning: string;
}

// === COMMIT 5: Unified Forensic Timeline ===
export interface InvestigationTimelineEvent {
  time: string;
  type: string;
  title: string;
  details?: string | string[];
  behavior_score?: number;
  position?: {
    lat: number;
    lon: number;
  };
  consistency_fraction?: number;
  configured_threshold?: number;
  evidence_role: string;
  flag_type?: string;
  mmsi?: string;
}

export interface InvestigationTimelineResult {
  mmsi: string;
  events: InvestigationTimelineEvent[];
  interpretation: string;
}

export interface ShipData {
  mmsi: string;
  name: string;
  code: string;
  vessel_type: string;
  operating_context: string;
  state: string;
  className: string;
  map_coords: {
    left_pct: number;
    top_pct: number;
  };
  bearing: string;
  speed: string;
  current_position: {
    lat: number;
    lon: number;
  };
  risk: number;
  vessel_analysis: VesselAnalysis;
  drift_forecast: DriftForecast;
  drift_backtrack: DriftBacktrack;
  attribution: Candidate;
  impact: ImpactForecast;
  surveillance: SurveillanceItem;
  integrity_flags?: AisIntegrityEvent[];
  response_queue?: ResponseQueueResult;
}

export interface ActiveCase {
  case_id: string;
  label: string;
  detected_time: string;
  satellite_scene: string;
  slick_area_km2: number;
  est_age: string;
  orientation: string;
  time: string;
  centroid: {
    lat: number;
    lon: number;
  };
}

// === COMMIT 6: Contextual Behavioral Anomaly Engine ===
export interface ContextualMetricSignal {
  observed: number;
  baseline_mean: number;
  baseline_std: number;
  standardized_deviation: number;
  severity: number;
}

export interface ContextualObservation {
  mmsi: string;
  time: string;
  operating_context: string;
  contextual_behavior_index: number;
  reasons: string[];
  metric_signals: Record<string, ContextualMetricSignal>;
}

export interface ContextualVesselEvent {
  time: string;
  type: string;
  severity: number;
  reasons: string[];
}

export interface ContextualVesselResult {
  mmsi: string;
  events: ContextualVesselEvent[];
}

export interface ContextualBehaviorResult {
  vessels?: ContextualVesselResult[];
  observations?: ContextualObservation[];
  score_meaning?: string;
}

// === COMMIT 7: Jurisdictional Escape & Intercept Feasibility ===
export interface EscapeBoundaryExit {
  eta_hours: number;
  time: string;
  position: {
    lat: number;
    lon: number;
  };
}

export interface InterceptionEstimate {
  base: string;
  position: {
    lat: number;
    lon: number;
  };
  vessel_eta_hours: number;
  patrol_eta_hours: number;
  time_margin_hours: number;
  time?: string;
}

export interface EscapeInterceptResult {
  scenario_label?: string;
  vessel_id?: string;
  jurisdiction_status?: string;
  projected_boundary_exit?: EscapeBoundaryExit | null;
  interception_estimate?: InterceptionEstimate | null;
  interpretation?: string;
}

export interface SarAisMatch {
  detection_id: string;
  mmsi: string;
  distance_m: number;
  time_delta_seconds: number;
  status: string;
  interpretation: string;
}

export interface UnmatchedSarDetection {
  detection_id: string;
  lat: number;
  lon: number;
  status: string;
  interpretation: string;
}

export interface UnmatchedAisPosition {
  mmsi: string;
  time: string;
  status: string;
  interpretation: string;
}

export interface AisTrustResult {
  sar_acquisition_time: string;
  matches: SarAisMatch[];
  unmatched_sar_detections: UnmatchedSarDetection[];
  ais_positions_without_sar_match_inside_scene: UnmatchedAisPosition[];
  score_meaning?: string;
}

export interface FullAnalysisResponse {
  active_case?: ActiveCase;
  ships: ShipData[];
  selected_mmsi?: string;
  overall_attribution?: Attribution;
  dead_reckoning?: DeadReckoningResult;
  ais_trust?: AisTrustResult;
  observation_plan?: ObservationPlanResult;
  forecast_update?: ForecastUpdateResult;
  ais_integrity?: AisIntegrityResult;
  temporal_risk?: TemporalRiskResult;
  investigation_timeline?: InvestigationTimelineResult;
  dossier_html?: string;
  overall_response_queue?: ResponseQueueResult;
  contextual_behavior?: ContextualBehaviorResult;
  escape_intercept?: EscapeInterceptResult;
  // Legacy / fallback fields:
  vessel_analysis: VesselAnalysis;
  drift_analysis: DriftAnalysis;
  attribution: Attribution;
  surveillance_queue: SurveillanceItem[];
}

