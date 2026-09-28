from backend.environment.impact import forecast_hypothetical_impact


def _check_score(name, value):
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be between 0 and 1")


def evaluate_pre_spill_candidate(
    mmsi,
    behavior_index,
    spill_opportunity,
    data_uncertainty,
    impact_case,
):
    """Score a vessel for surveillance before any spill is detected."""
    _check_score("behavior_index", behavior_index)
    _check_score("spill_opportunity", spill_opportunity)
    _check_score("data_uncertainty", data_uncertainty)

    impact = forecast_hypothetical_impact(impact_case)

    # Behaviour × opportunity estimates incident likelihood.
    incident_proxy = behavior_index * spill_opportunity

    # Consequence-aware priority also considers ecological exposure
    # and uncertainty that may justify closer monitoring.
    priority = incident_proxy * impact["impact_index"] * data_uncertainty

    return {
        "mmsi": mmsi,
        "incident_proxy": round(incident_proxy, 4),
        "behavior_index": behavior_index,
        "spill_opportunity": spill_opportunity,
        "data_uncertainty": data_uncertainty,
        "potential_impact_index": impact["impact_index"],
        "priority_index": round(priority, 4),
        "impact_forecast": impact,
        "score_meaning": (
            "Prototype surveillance ranking index; not a spill probability, "
            "attribution score, or guilt score."
        ),
    }


def rank_surveillance_candidates(candidates):
    """Rank evaluated vessels from highest to lowest surveillance priority."""
    return sorted(
        candidates,
        key=lambda item: item["priority_index"],
        reverse=True,
    )