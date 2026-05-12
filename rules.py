"""Rule engine — loads asset-class rules from config.yaml and classifies securities.

Each rule has a matcher block, a schedule, and optional date-of-applicability bounds.
The first rule whose matcher (and date condition, if any) matches wins.
"""

from datetime import date as _date


def _matches(rule_match: dict, asset_class: str, instrument: str, category: str, name: str) -> bool:
    name_u = (name or "").upper().strip()
    ac = (asset_class or "").strip()
    inst = (instrument or "").strip()
    cat = (category or "").strip()

    if "asset_class" in rule_match and rule_match["asset_class"] != ac:
        return False
    if "instrument" in rule_match and rule_match["instrument"] != inst:
        return False
    if "category" in rule_match and rule_match["category"] != cat:
        return False
    if "name_equals" in rule_match:
        if name_u != rule_match["name_equals"].upper().strip():
            return False
    if "name_contains" in rule_match:
        if rule_match["name_contains"].upper() not in name_u:
            return False
    return True


def _date_window_ok(rule, event_date):
    """Check applies_from_date and applies_until_date bounds."""
    if event_date is None:
        return True
    af = rule.get("applies_from_date")
    if af:
        if isinstance(af, str):
            af = _date.fromisoformat(af)
        if event_date < af:
            return False
    au = rule.get("applies_until_date")
    if au:
        if isinstance(au, str):
            au = _date.fromisoformat(au)
        if event_date >= au:
            return False
    return True


def classify(rules, asset_class, instrument, category, name, event_date=None):
    """Return the matching rule dict; if none match, return an Unclassified stub."""
    for rule in rules:
        if not _matches(rule.get("match", {}), asset_class, instrument, category, name):
            continue
        if not _date_window_ok(rule, event_date):
            continue
        return rule
    return {
        "name": "Unclassified",
        "schedule": {},
        "parking_fund": None,
    }


def normalise_schedule(schedule):
    return {int(k): float(v) for k, v in (schedule or {}).items()}
