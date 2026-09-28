def _unit_interval(name, value):
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be between 0 and 1")


def calculate_surveillance_priority(
    behavior_index,
    spill_opportunity,
    potential_ecological_impact,
    data_uncertainty,
):
    """
    Calculate a prototype surveillance priority index.

    Each input must be normalized to 0..1.
    This is a queueing heuristic, not a calibrated probability.
    """
    components = {
        "behavior_index": behavior_index,
        "spill_opportunity": spill_opportunity,
        "potential_ecological_impact": potential_ecological_impact,
        "data_uncertainty": data_uncertainty,
    }

    for name, value in components.items():
        _unit_interval(name, value)

    priority = (
        behavior_index
        * spill_opportunity
        * potential_ecological_impact
        * data_uncertainty
    )

    return {
        **components,
        "surveillance_priority_index": priority,
        "interpretation": (
            "Prototype prioritization heuristic; not a spill probability "
            "or attribution score."
        ),
    }