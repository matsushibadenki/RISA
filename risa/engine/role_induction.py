from __future__ import annotations

import hashlib
import json

from risa.core.models import Event
INDUCED_ROLE_PREFIX = "struct_role:"


def effective_event_target_roles(event: Event) -> list[str]:
    """Prefer supplied roles and otherwise derive one from the target's relation position."""
    supplied = sorted({_normalize_label(role) for role in event.target_roles})
    if supplied:
        return supplied
    induced = induced_target_role(
        target=event.target,
        entity_bindings=event.entity_bindings,
        entity_relations=event.entity_relations,
    )
    return [induced] if induced else []


def effective_query_target_roles(
    *,
    target: str | None,
    supplied_roles: list[str],
    entity_bindings: dict[str, str],
    entity_relations: list[dict[str, str]],
    enable_role_induction: bool = True,
) -> list[str]:
    supplied = sorted({_normalize_label(role) for role in supplied_roles})
    if supplied or not enable_role_induction:
        return supplied
    induced = induced_target_role(
        target=target,
        entity_bindings=entity_bindings,
        entity_relations=entity_relations,
    )
    return [induced] if induced else []


def induced_target_role(
    *,
    target: str | None,
    entity_bindings: dict[str, str],
    entity_relations: list[dict[str, str]],
) -> str:
    signature = target_relation_position_signature(
        target=target,
        entity_bindings=entity_bindings,
        entity_relations=entity_relations,
    )
    if not signature:
        return ""
    encoded = json.dumps(signature, separators=(",", ":"))
    return INDUCED_ROLE_PREFIX + hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]


def target_relation_position_signature(
    *,
    target: str | None,
    entity_bindings: dict[str, str],
    entity_relations: list[dict[str, str]],
) -> tuple[str, ...]:
    """Describe one entity by relation direction and type, independent of variable names."""
    if not target or not entity_bindings or not entity_relations:
        return ()
    normalized_target = _normalize_label(target)
    bindings = {
        _normalize_label(variable): _normalize_label(identity)
        for variable, identity in entity_bindings.items()
    }
    target_variables = {
        variable for variable, identity in bindings.items() if identity == normalized_target
    }
    if not target_variables:
        return ()
    descriptors: set[str] = set()
    for raw_relation in entity_relations:
        source = _normalize_label(str(raw_relation.get("source", "")))
        relation = _normalize_label(str(raw_relation.get("relation", "")))
        destination = _normalize_label(str(raw_relation.get("target", "")))
        if not source or not relation or not destination:
            continue
        source_is_target = source in target_variables
        destination_is_target = destination in target_variables
        if source_is_target and destination_is_target:
            descriptors.add(f"self:{relation}")
        elif source_is_target:
            descriptors.add(f"out:{relation}")
        elif destination_is_target:
            descriptors.add(f"in:{relation}")
    return tuple(sorted(descriptors))


def is_induced_role(role: str) -> bool:
    return _normalize_label(role).startswith(INDUCED_ROLE_PREFIX)


def _normalize_label(value: str) -> str:
    return value.strip().lower().replace(" ", "_")
