def calculate_data_uncertainty(signal_scores, weights):
    """Combine scenario-supplied, normalized data-uncertainty signals."""
    if not signal_scores:
        raise ValueError("Provide at least one uncertainty signal")
    if set(signal_scores) != set(weights):
        raise ValueError("Signal names and weight names must match")

    weight_total = sum(weights.values())
    if weight_total <= 0:
        raise ValueError("At least one uncertainty weight must be positive")

    contributions = {}
    weighted_total = 0.0

    for name, uncertainty in signal_scores.items():
        weight = weights[name]

        if not 0.0 <= uncertainty <= 1.0:
            raise ValueError(f"{name} uncertainty must be between 0 and 1")
        if weight < 0.0:
            raise ValueError(f"{name} weight cannot be negative")

        contributions[name] = uncertainty * weight
        weighted_total += contributions[name]

    return {
        "data_uncertainty": weighted_total / weight_total,
        "signals": signal_scores,
        "weights": weights,
        "weighted_contributions": contributions,
    }