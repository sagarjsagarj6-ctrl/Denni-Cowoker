"""Capability registry for dynamically selected roles."""

ROLE_CAPABILITIES = {
    "engineering": {"requirements", "compatibility", "design"},
    "manufacturing": {"process", "tooling", "work_instructions"},
    "quality": {"quality_history", "failure_modes", "controls"},
    "supply_chain": {"supplier", "capacity", "logistics"},
    "cost": {"cost_model", "commercial"},
    "contract": {"contract", "warranty", "liability"},
    "regulatory": {"certification", "compliance", "change_control"},
    "validation": {"test", "qualification", "verification"},
    "reviewer": {"synthesis", "contradiction_detection", "decision"},
}


def capabilities_for(role: str) -> set[str]:
    """Return capability labels for a role."""
    return ROLE_CAPABILITIES.get(role, set())
