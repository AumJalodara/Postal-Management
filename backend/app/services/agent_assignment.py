import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import asc, nulls_first

from app.models.enums import PickupStatus
from app.models.delivery_agent import DeliveryAgent
from app.models.pickup import PickupRequest, PickupStatusHistory
from app.models.operational_history import OperationalHistory
from app.services.postal_location_service import postal_location_service
from app.services.geospatial_engine import haversine_distance, InvalidCoordinateError
from app.config import settings

logger = logging.getLogger(__name__)


def assign_pickup_agent(db: Session, pickup: PickupRequest) -> Optional[DeliveryAgent]:
    """
    Module 4 Step 4 Intelligent Agent Assignment:
    1. Filter eligible agents (is_available=True, service_area=pickup.pickup_pin)
    2. Retrieve pickup and agent coordinates via postal_location_service
    3. Calculate Geographic Distance using geospatial_engine
    4. Normalize Distance and Workload
    5. Calculate combined deterministic score:
       score = (distance_weight * norm_dist) + (workload_weight * norm_workload)
    6. Deterministic Tie-breaking:
       - score ASC
       - raw workload ASC
       - last_assigned_at ASC NULLS FIRST
       - id ASC
    7. Atomically lock and assign the best candidate, producing an explainable audit record.
    """
    if pickup.status != PickupStatus.PENDING:
        logger.info(f"Pickup #{pickup.id} is already in status {pickup.status.value}, skipping assignment.")
        return None

    # 1. Eligibility Filter
    candidates = (
        db.query(DeliveryAgent)
        .filter(
            DeliveryAgent.is_available.is_(True),
            DeliveryAgent.service_area == pickup.pickup_pin
        )
        .all()
    )

    if not candidates:
        logger.info(f"No eligible delivery agent found for PIN {pickup.pickup_pin}. Pickup #{pickup.id} remains PENDING.")
        return None

    # 2. Resolve Pickup Coordinate
    pickup_loc = postal_location_service.get_location_for_pin(pickup.pickup_pin)
    pickup_lat = pickup_loc.get("latitude") if pickup_loc else None
    pickup_lon = pickup_loc.get("longitude") if pickup_loc else None

    scored_candidates = []

    # 3. Collect Raw Values & Distances
    for candidate in candidates:
        agent_loc = postal_location_service.get_location_for_pin(candidate.service_area)
        agent_lat = agent_loc.get("latitude") if agent_loc else None
        agent_lon = agent_loc.get("longitude") if agent_loc else None

        dist_km = None
        if None not in (pickup_lat, pickup_lon, agent_lat, agent_lon):
            try:
                dist_km = haversine_distance(agent_lat, agent_lon, pickup_lat, pickup_lon)
            except InvalidCoordinateError:
                pass

        scored_candidates.append({
            "agent": candidate,
            "dist_km": dist_km,
            "workload": candidate.active_pickup_count,
            "last_assigned_at": candidate.last_assigned_at,
            "id": candidate.id
        })

    # 4. Normalization
    valid_distances = [c["dist_km"] for c in scored_candidates if c["dist_km"] is not None]
    max_dist = max(valid_distances) if valid_distances else 0.0

    workloads = [c["workload"] for c in scored_candidates]
    max_workload = max(workloads) if workloads else 0

    dist_weight = settings.AGENT_DISTANCE_WEIGHT
    workload_weight = settings.AGENT_WORKLOAD_WEIGHT

    # Fallback to zero if weights are configured strangely
    if dist_weight < 0: dist_weight = 0.0
    if workload_weight < 0: workload_weight = 0.0

    for c in scored_candidates:
        c["norm_dist"] = (c["dist_km"] / max_dist) if (c["dist_km"] is not None and max_dist > 0) else 0.0
        c["norm_workload"] = (c["workload"] / max_workload) if (max_workload > 0) else 0.0
        c["score"] = (dist_weight * c["norm_dist"]) + (workload_weight * c["norm_workload"])

    # 5. Deterministic Sort & Tie-Breaking
    scored_candidates.sort(key=lambda c: (
        c["score"],
        c["workload"],
        0 if c["last_assigned_at"] is None else 1,
        c["last_assigned_at"].timestamp() if c["last_assigned_at"] else 0.0,
        c["id"]
    ))

    best_candidate_info = scored_candidates[0]
    best_agent_id = best_candidate_info["id"]

    # 6. Concurrency-Safe Final Assignment
    bind = db.get_bind()
    candidate_query = db.query(DeliveryAgent).filter(DeliveryAgent.id == best_agent_id)
    if bind.dialect.name == "postgresql":
        candidate_query = candidate_query.with_for_update()

    final_candidate = candidate_query.first()
    if not final_candidate or not final_candidate.is_available:
        logger.warning(f"Selected agent #{best_agent_id} became unavailable during assignment. Leaving pickup #{pickup.id} PENDING.")
        return None

    now = datetime.now(timezone.utc)

    # 7. Explainable Audit Log
    dist_val = best_candidate_info["dist_km"]
    dist_str = f"{dist_val:.2f} km" if dist_val is not None else "Unknown"
    norm_dist = best_candidate_info["norm_dist"]
    norm_wk = best_candidate_info["norm_workload"]
    score_val = best_candidate_info["score"]

    reason_str = (
        f"Assigned to Delivery Agent #{final_candidate.id} for PIN {pickup.pickup_pin}. "
        f"[Distance: {dist_str} (weight {dist_weight}, norm {norm_dist:.2f}), "
        f"Workload: {final_candidate.active_pickup_count} (weight {workload_weight}, norm {norm_wk:.2f}), "
        f"Final Score: {score_val:.4f}]"
    )

    pickup.assigned_agent_id = final_candidate.id
    pickup.status = PickupStatus.ASSIGNED

    final_candidate.active_pickup_count += 1
    final_candidate.last_assigned_at = now

    history = PickupStatusHistory(
        pickup_id=pickup.id,
        old_status=PickupStatus.PENDING.value,
        new_status=PickupStatus.ASSIGNED.value,
        changed_by=None,
        changed_by_role="SYSTEM",
        reason=reason_str
    )
    
    op_hist = OperationalHistory(
        event_type="AGENT_ASSIGNED",
        entity_type="pickup_request",
        entity_id=pickup.id,
        actor_user_id=None,
        agent_id=final_candidate.id,
        previous_status=PickupStatus.PENDING.value,
        new_status=PickupStatus.ASSIGNED.value,
        description=reason_str,
        metadata_={
            "distance_km": dist_val,
            "workload": final_candidate.active_pickup_count,
            "score": score_val
        }
    )

    db.add(pickup)
    db.add(final_candidate)
    db.add(history)
    db.add(op_hist)
    db.commit()
    db.refresh(pickup)
    db.refresh(final_candidate)

    logger.info(f"Assigned Pickup #{pickup.id} to Agent #{final_candidate.id} (Score: {score_val:.4f}, New workload: {final_candidate.active_pickup_count})")
    return final_candidate
