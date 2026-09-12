from __future__ import annotations

import hashlib
import json

from risa.core.models import Event


INDUCED_ROLE_PREFIX = "struct_role:"
MAX_ROLE_SIGNATURE_HOPS = 2
MAX_ROLE_REFINEMENTS_PER_BASE = 8


def effective_event_target_roles(event: Event) -> list[str]:
    """Prefer supplied roles and otherwise derive the target's one-hop role."""
    supplied = _normalized_roles(event.target_roles)
    if supplied:
        return supplied
    induced = induced_entity_role(
        identity=event.target,
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
    supplied = _normalized_roles(supplied_roles)
    if supplied or not enable_role_induction:
        return supplied
    return [
        role
        for role, _ in induced_entity_role_hierarchy(
            identity=target,
            entity_bindings=entity_bindings,
            entity_relations=entity_relations,
        )
    ]


def effective_event_actor_roles(event: Event) -> list[str]:
    """Prefer supplied actor roles and otherwise derive the actor's one-hop role."""
    supplied = _normalized_roles(event.actor_roles)
    if supplied:
        return supplied
    induced = induced_entity_role(
        identity=event.actor,
        entity_bindings=event.entity_bindings,
        entity_relations=event.entity_relations,
    )
    return [induced] if induced else []


def effective_query_actor_roles(
    *,
    actor: str | None,
    supplied_roles: list[str],
    entity_bindings: dict[str, str],
    entity_relations: list[dict[str, str]],
    enable_role_induction: bool = True,
) -> list[str]:
    supplied = _normalized_roles(supplied_roles)
    if supplied or not enable_role_induction:
        return supplied
    return [
        role
        for role, _ in induced_entity_role_hierarchy(
            identity=actor,
            entity_bindings=entity_bindings,
            entity_relations=entity_relations,
        )
    ]


def effective_event_entity_role_bindings(event: Event) -> dict[str, list[str]]:
    """Resolve a one-hop role for each bound entity that lacks supplied roles."""
    resolved: dict[str, list[str]] = {}
    for variable, identity in event.entity_bindings.items():
        normalized_variable = _normalize_label(variable)
        supplied = _normalized_roles(
            event.entity_role_bindings.get(
                variable, event.entity_role_bindings.get(normalized_variable, [])
            )
        )
        if supplied:
            resolved[normalized_variable] = supplied
            continue
        induced = induced_entity_role(
            identity=identity,
            entity_bindings=event.entity_bindings,
            entity_relations=event.entity_relations,
        )
        if induced:
            resolved[normalized_variable] = [induced]
    return resolved


def effective_query_entity_role_bindings(
    *,
    supplied_bindings: dict[str, list[str]],
    entity_bindings: dict[str, str],
    entity_relations: list[dict[str, str]],
    enable_role_induction: bool = True,
) -> dict[str, list[str]]:
    resolved: dict[str, list[str]] = {}
    for variable, identity in entity_bindings.items():
        normalized_variable = _normalize_label(variable)
        supplied = _normalized_roles(
            supplied_bindings.get(
                variable, supplied_bindings.get(normalized_variable, [])
            )
        )
        if supplied or not enable_role_induction:
            if supplied:
                resolved[normalized_variable] = supplied
            continue
        hierarchy = induced_entity_role_hierarchy(
            identity=identity,
            entity_bindings=entity_bindings,
            entity_relations=entity_relations,
        )
        if hierarchy:
            resolved[normalized_variable] = [role for role, _ in hierarchy]
    return resolved


def induced_target_role_hierarchy(event: Event) -> list[tuple[str, tuple[str, ...]]]:
    return induced_entity_role_hierarchy(
        identity=event.target,
        entity_bindings=event.entity_bindings,
        entity_relations=event.entity_relations,
    )


def induced_entity_role_hierarchy(
    *,
    identity: str | None,
    entity_bindings: dict[str, str],
    entity_relations: list[dict[str, str]],
    max_hops: int = MAX_ROLE_SIGNATURE_HOPS,
) -> list[tuple[str, tuple[str, ...]]]:
    """Return unique one-to-N-hop structural roles, shallowest first."""
    if max_hops < 1:
        return []
    hierarchy: list[tuple[str, tuple[str, ...]]] = []
    previous_signature: tuple[str, ...] = ()
    for hop_count in range(1, min(max_hops, MAX_ROLE_SIGNATURE_HOPS) + 1):
        signature = entity_relation_position_signature(
            identity=identity,
            entity_bindings=entity_bindings,
            entity_relations=entity_relations,
            max_hops=hop_count,
        )
        if not signature or signature == previous_signature:
            continue
        hierarchy.append((_role_id(signature), signature))
        previous_signature = signature
    return hierarchy


def induced_entity_role(
    *,
    identity: str | None,
    entity_bindings: dict[str, str],
    entity_relations: list[dict[str, str]],
    max_hops: int = 1,
) -> str:
    signature = entity_relation_position_signature(
        identity=identity,
        entity_bindings=entity_bindings,
        entity_relations=entity_relations,
        max_hops=max_hops,
    )
    return _role_id(signature) if signature else ""


def induced_target_role(
    *,
    target: str | None,
    entity_bindings: dict[str, str],
    entity_relations: list[dict[str, str]],
    max_hops: int = 1,
) -> str:
    return induced_entity_role(
        identity=target,
        entity_bindings=entity_bindings,
        entity_relations=entity_relations,
        max_hops=max_hops,
    )


def target_relation_position_signature(
    *,
    target: str | None,
    entity_bindings: dict[str, str],
    entity_relations: list[dict[str, str]],
    max_hops: int = 1,
) -> tuple[str, ...]:
    return entity_relation_position_signature(
        identity=target,
        entity_bindings=entity_bindings,
        entity_relations=entity_relations,
        max_hops=max_hops,
    )


def entity_relation_position_signature(
    *,
    identity: str | None,
    entity_bindings: dict[str, str],
    entity_relations: list[dict[str, str]],
    max_hops: int = 1,
) -> tuple[str, ...]:
    """Describe a bound entity by variable-name-independent relation paths."""
    if not identity or not entity_bindings or not entity_relations or max_hops < 1:
        return ()
    normalized_identity = _normalize_label(identity)
    bindings = {
        _normalize_label(variable): _normalize_label(bound_identity)
        for variable, bound_identity in entity_bindings.items()
    }
    roots = {
        variable
        for variable, bound_identity in bindings.items()
        if bound_identity == normalized_identity
    }
    if not roots:
        return ()
    relations = [
        (
            _normalize_label(str(raw.get("source", ""))),
            _normalize_label(str(raw.get("relation", ""))),
            _normalize_label(str(raw.get("target", ""))),
        )
        for raw in entity_relations
    ]
    relations = [
        item
        for item in relations
        if all(item) and item[0] in bindings and item[2] in bindings
    ]
    descriptors: set[str] = set()
    frontier: set[tuple[str, tuple[str, ...], frozenset[str]]] = {
        (variable, (), frozenset({variable})) for variable in roots
    }
    for depth in range(1, min(max_hops, MAX_ROLE_SIGNATURE_HOPS) + 1):
        next_frontier: set[
            tuple[str, tuple[str, ...], frozenset[str]]
        ] = set()
        for variable, path, visited in frontier:
            for source, relation, destination in relations:
                if source == variable and destination == variable:
                    step, neighbor = f"self:{relation}", variable
                elif source == variable:
                    step, neighbor = f"out:{relation}", destination
                elif destination == variable:
                    step, neighbor = f"in:{relation}", source
                else:
                    continue
                extended = (*path, step)
                descriptor = step if depth == 1 else f"{depth}:" + "|".join(extended)
                descriptors.add(descriptor)
                if neighbor not in visited:
                    next_frontier.add((neighbor, extended, visited | {neighbor}))
        frontier = next_frontier
        if not frontier:
            break
    return tuple(sorted(descriptors))


def is_induced_role(role: str) -> bool:
    return _normalize_label(role).startswith(INDUCED_ROLE_PREFIX)


def _role_id(signature: tuple[str, ...]) -> str:
    encoded = json.dumps(signature, separators=(",", ":"))
    return INDUCED_ROLE_PREFIX + hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]


def _normalized_roles(roles: list[str]) -> list[str]:
    return sorted({_normalize_label(role) for role in roles if _normalize_label(role)})


def _normalize_label(value: str) -> str:
    return value.strip().lower().replace(" ", "_")
