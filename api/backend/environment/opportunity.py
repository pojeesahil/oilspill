def calculate_spill_opportunity(signal_scores, weights):
    """Combine scenario-supplied, normalized opportunity signals.

    signal_scores and weights must have the same keys.
    Scores must be in [0, 1]. Weights must be non-negative.
    """
    if not signal_scores:
        raise ValueError("Provide at least one spill-opportunity signal")
    if set(signal_scores) != set(weights):
        raise ValueError("Signal names and weight names must match")

    weight_total = sum(weights.values())
    if weight_total <= 0:
        raise ValueError("At least one opportunity weight must be positive")

    contributions = {}
    weighted_total = 0.0

    for name, score in signal_scores.items():
        weight = weights[name]

        if not 0.0 <= score <= 1.0:
            raise ValueError(f"{name} score must be between 0 and 1")
        if weight < 0.0:
            raise ValueError(f"{name} weight cannot be negative")

        contribution = score * weight
        contributions[name] = contribution
        weighted_total += contribution

    return {
        "spill_opportunity": weighted_total / weight_total,
        "signals": signal_scores,
        "weights": weights,
        "weighted_contributions": contributions,
        "score_meaning": (
            "Prototype spill-opportunity index from configured signals; "
            "not a spill probability."
        ),
    }