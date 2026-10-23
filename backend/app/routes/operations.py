from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session, joinedload

from app.database.connection import get_db
from app.config import settings
from app.auth.limiter import limiter
from app.models.user import User
from app.models.delivery_agent import DeliveryAgent
from app.models.pickup import PickupRequest
from app.models.parcel import Parcel
from app.models.enums import UserRole, PickupStatus
from app.models.operational_history import OperationalHistory
from app.schemas.common import ApiResponse
from app.schemas.operations import (
    OperationsAgentSummary,
    OperationsRouteResponse,
    OperationsETAResponse,
    OperationsAgentDetail,
    OperationsPickupSummary,
    OperationsHistoryResponse,
    OperationsHistoryListResponse,
    OperationsAssistantRequest,
    OperationsAssistantResponse,
    OperationsCitizenSummary,
    OperationsCitizenMetrics,
    OperationsCitizensResponse,
    OperationsCitizenParcelItem
)

from app.auth.dependencies import require_roles
from app.services.route_optimization import build_optimized_route
from app.services.eta_estimation import calculate_eta
from app.services.llm_provider import get_llm_provider, LLMProviderError
from dataclasses import asdict

router = APIRouter(prefix="/operations", tags=["Operations API"])

def _get_agent_with_pickups(db: Session, agent_id: int) -> DeliveryAgent:
    agent = db.query(DeliveryAgent).options(joinedload(DeliveryAgent.user)).filter(DeliveryAgent.id == agent_id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "AGENT_NOT_FOUND", "message": f"Delivery Agent #{agent_id} not found."}
        )
    return agent

def _get_route_result(db: Session, agent: DeliveryAgent):
    # Fetch routable assigned pickups
    pickups = (
        db.query(PickupRequest)
        .filter(PickupRequest.assigned_agent_id == agent.id)
        .filter(PickupRequest.status.in_([PickupStatus.ASSIGNED, PickupStatus.ACCEPTED]))
        .all()
    )
    return build_optimized_route(
        agent_id=agent.id,
        agent_service_pin=agent.service_area,
        assigned_pickups=pickups
    )

@router.get("/agents", response_model=ApiResponse[List[OperationsAgentSummary]])
def list_agents(
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_roles(UserRole.ADMIN))
):
    """
    Retrieve operational summary for all eligible delivery agents.
    """
    agents = db.query(DeliveryAgent).options(joinedload(DeliveryAgent.user)).all()
    results = []
    for agent in agents:
        results.append(OperationsAgentSummary(
            agent_id=agent.id,
            name=agent.user.name,
            phone=agent.user.phone,
            service_area=agent.service_area,
            is_available=agent.is_available,
            active_pickup_count=agent.active_pickup_count,
            last_assigned_at=agent.last_assigned_at
        ))
    return ApiResponse.ok(data=results)

@router.get("/agents/{agent_id}/route", response_model=ApiResponse[OperationsRouteResponse])
def get_agent_route(
    agent_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_roles(UserRole.ADMIN))
):
    """
    Obtain the current optimized geographic route for a specific agent.
    """
    agent = _get_agent_with_pickups(db, agent_id)
    route_result = _get_route_result(db, agent)
    # The dataclass maps directly to the Pydantic schema in simple cases, 
    # but let's parse it safely via dict
    # Record history
    hist = OperationalHistory(
        event_type="ROUTE_GENERATED",
        entity_type="delivery_agent",
        entity_id=agent.id,
        actor_user_id=current_admin.id,
        agent_id=agent.id,
        metadata_={
            "route_distance_km": route_result.optimized_distance_km,
            "stop_count": len(route_result.stops),
            "algorithm": route_result.algorithm
        }
    )
    db.add(hist)
    db.commit()

    return ApiResponse.ok(data=OperationsRouteResponse(**asdict(route_result)))

@router.get("/agents/{agent_id}/eta", response_model=ApiResponse[OperationsETAResponse])
def get_agent_eta(
    agent_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_roles(UserRole.ADMIN))
):
    """
    Obtain ETA estimation for a specific agent's current route.
    """
    agent = _get_agent_with_pickups(db, agent_id)
    route_result = _get_route_result(db, agent)
    eta_result = calculate_eta(route=route_result)
    from dataclasses import asdict
    
    # Record history
    hist = OperationalHistory(
        event_type="ETA_CALCULATED",
        entity_type="delivery_agent",
        entity_id=agent.id,
        actor_user_id=current_admin.id,
        agent_id=agent.id,
        metadata_={
            "total_eta_minutes": eta_result.total_eta_minutes
        }
    )
    db.add(hist)
    db.commit()

    return ApiResponse.ok(data=OperationsETAResponse(**asdict(eta_result)))

@router.get("/agents/{agent_id}", response_model=ApiResponse[OperationsAgentDetail])
def get_agent_detail(
    agent_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_roles(UserRole.ADMIN))
):
    """
    Retrieve comprehensive operations detail for a specific agent.
    """
    agent = _get_agent_with_pickups(db, agent_id)
    route_result = _get_route_result(db, agent)
    eta_result = calculate_eta(route=route_result)
    
    from dataclasses import asdict
    summary = OperationsAgentSummary(
        agent_id=agent.id,
        name=agent.user.name,
        phone=agent.user.phone,
        service_area=agent.service_area,
        is_available=agent.is_available,
        active_pickup_count=agent.active_pickup_count,
        last_assigned_at=agent.last_assigned_at
    )
    
    detail = OperationsAgentDetail(
        agent=summary,
        route=OperationsRouteResponse(**asdict(route_result)),
        eta=OperationsETAResponse(**asdict(eta_result))
    )
    return ApiResponse.ok(data=detail)

@router.get("/pickups", response_model=ApiResponse[List[OperationsPickupSummary]])
def list_pickups(
    agent_id: int = None,
    status: str = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_roles(UserRole.ADMIN))
):
    """
    Provide authorized operational visibility into pickups.
    """
    query = db.query(PickupRequest)
    
    if agent_id is not None:
        query = query.filter(PickupRequest.assigned_agent_id == agent_id)
    if status is not None:
        try:
            status_enum = PickupStatus(status.upper())
            query = query.filter(PickupRequest.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail={"code": "INVALID_STATUS", "message": f"Invalid pickup status: {status}"}
            )
            
    pickups = query.order_by(PickupRequest.updated_at.desc()).all()
    results = []
    for p in pickups:
        results.append(OperationsPickupSummary(
            id=p.id,
            parcel_id=p.parcel_id,
            requester_id=p.requester_id,
            assigned_agent_id=p.assigned_agent_id,
            status=p.status.value if hasattr(p.status, "value") else p.status,
            pickup_pin=p.pickup_pin,
            requested_date=str(p.requested_date)
        ))
        
    return ApiResponse.ok(data=results)

from datetime import datetime

@router.get("/history", response_model=ApiResponse[OperationsHistoryListResponse])
def get_operational_history(
    entity_type: str = None,
    entity_id: int = None,
    event_type: str = None,
    agent_id: int = None,
    start_date: datetime = None,
    end_date: datetime = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_roles(UserRole.ADMIN))
):
    """
    Retrieve paginated operational history audit logs.
    """
    query = db.query(OperationalHistory)
    
    if entity_type:
        query = query.filter(OperationalHistory.entity_type == entity_type)
    if entity_id:
        query = query.filter(OperationalHistory.entity_id == entity_id)
    if event_type:
        query = query.filter(OperationalHistory.event_type == event_type)
    if agent_id:
        query = query.filter(OperationalHistory.agent_id == agent_id)
    if start_date:
        query = query.filter(OperationalHistory.created_at >= start_date)
    if end_date:
        query = query.filter(OperationalHistory.created_at <= end_date)
        
    total_count = query.count()
    
    items = query.order_by(OperationalHistory.created_at.desc(), OperationalHistory.id.desc()) \
                 .offset((page - 1) * page_size) \
                 .limit(page_size) \
                 .all()
                 
    results = []
    for item in items:
        results.append(OperationsHistoryResponse(
            id=item.id,
            event_type=item.event_type,
            entity_type=item.entity_type,
            entity_id=item.entity_id,
            actor_user_id=item.actor_user_id,
            agent_id=item.agent_id,
            previous_status=item.previous_status,
            new_status=item.new_status,
            description=item.description,
            metadata=item.metadata_,
            created_at=item.created_at
        ))
        
    return ApiResponse.ok(data=OperationsHistoryListResponse(
        items=results,
        page=page,
        page_size=page_size,
        total_count=total_count
    ))

import json

@router.post("/assistant", response_model=ApiResponse[OperationsAssistantResponse])
@limiter.limit(settings.RATE_LIMIT_OPS_ASSISTANT)
def operations_assistant(
    request: Request,
    body: OperationsAssistantRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_roles(UserRole.ADMIN))
):
    """
    AI assistant restricted to operational data context.
    Uses real Groq LLM to answer questions about agent workload, routes, ETA, and history.
    """
    try:
        # Load necessary context for the AI
        agents = db.query(DeliveryAgent).all()
        agent_data = []
        for ag in agents:
            agent_data.append({
                "agent_id": ag.id,
                "service_area": ag.service_area,
                "active_pickups": ag.active_pickup_count,
                "is_available": ag.is_available
            })
            
        recent_history = db.query(OperationalHistory).order_by(OperationalHistory.created_at.desc()).limit(20).all()
        history_data = []
        for h in recent_history:
            history_data.append({
                "id": h.id,
                "event": h.event_type,
                "entity": h.entity_type,
                "entity_id": h.entity_id,
                "agent_id": h.agent_id,
                "time": str(h.created_at),
                "desc": h.description,
                "metadata": h.metadata_
            })

        # Citizen and consignment metrics for AI
        total_cit = db.query(User).filter(User.role == UserRole.CITIZEN).count()
        total_parcels = db.query(Parcel).count()
        total_pickups = db.query(PickupRequest).count()
        citizen_data = {
            "total_registered_citizens": total_cit,
            "total_parcels_booked": total_parcels,
            "total_pickups_requested": total_pickups,
        }

        system_prompt = (
            "You are an AI Operations Assistant for a Smart Postal Management System. "
            "You must answer the user's questions based strictly on the provided operational context below.\n\n"
            "If the required information is unavailable in the context, say exactly: "
            "'The available operational data is insufficient to answer that.'\n\n"
            "Do not invent operational facts. Do not output raw JSON, write a human-readable response.\n\n"
            f"CITIZEN & BOOKINGS CONTEXT: {json.dumps(citizen_data)}\n\n"
            f"AGENT WORKLOAD CONTEXT: {json.dumps(agent_data)}\n\n"
            f"RECENT OPERATIONAL HISTORY: {json.dumps(history_data)}"
        )

        llm = get_llm_provider()
        answer = llm.generate(system_prompt=system_prompt, user_message=body.query)

        return ApiResponse.ok(data=OperationsAssistantResponse(answer=answer))
    except LLMProviderError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "AI_UNAVAILABLE", "message": str(e)}
        )


@router.get("/citizens", response_model=ApiResponse[OperationsCitizensResponse])
def get_operations_citizens(
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_roles(UserRole.ADMIN))
):
    """
    Retrieve operational metrics and registry of all citizens,
    including registration status, total parcels booked, active consignments, and revenue.
    """
    citizens = (
        db.query(User)
        .filter(User.role == UserRole.CITIZEN)
        .order_by(User.created_at.desc())
        .all()
    )

    citizen_summaries = []
    total_parcels = 0
    total_pickups = 0
    total_revenue = 0.0
    citizens_with_bookings_count = 0

    for cit in citizens:
        parcels = db.query(Parcel).filter(Parcel.sender_id == cit.id).order_by(Parcel.created_at.desc()).all()
        pickups = db.query(PickupRequest).filter(PickupRequest.requester_id == cit.id).all()

        parcel_count = len(parcels)
        pickup_count = len(pickups)
        total_parcels += parcel_count
        total_pickups += pickup_count

        spent = sum(float(p.price or 0.0) for p in parcels)
        total_revenue += spent

        active_count = sum(1 for p in parcels if p.status not in ["DELIVERED", "RETURNED", "CANCELLED"])
        delivered_count = sum(1 for p in parcels if p.status == "DELIVERED")

        if parcel_count > 0 or pickup_count > 0:
            citizens_with_bookings_count += 1

        last_booking = parcels[0].created_at if parcels else None

        citizen_summaries.append(OperationsCitizenSummary(
            citizen_id=cit.id,
            name=cit.name,
            email=cit.email,
            phone=cit.phone,
            is_active=cit.is_active,
            registered_at=cit.created_at,
            parcels_booked_count=parcel_count,
            active_parcels_count=active_count,
            delivered_parcels_count=delivered_count,
            pickups_requested_count=pickup_count,
            total_spent=round(spent, 2),
            last_booking_date=last_booking
        ))

    total_cit = len(citizens)
    avg_parcels = round(total_parcels / total_cit, 2) if total_cit > 0 else 0.0

    metrics = OperationsCitizenMetrics(
        total_registered_citizens=total_cit,
        citizens_with_bookings=citizens_with_bookings_count,
        total_parcels_booked=total_parcels,
        total_pickups_requested=total_pickups,
        total_revenue=round(total_revenue, 2),
        average_parcels_per_citizen=avg_parcels
    )

    return ApiResponse.ok(data=OperationsCitizensResponse(
        metrics=metrics,
        citizens=citizen_summaries
    ))


@router.get("/citizens/{citizen_id}/parcels", response_model=ApiResponse[List[OperationsCitizenParcelItem]])
def get_citizen_parcels(
    citizen_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_roles(UserRole.ADMIN))
):
    """
    Retrieve all consignments booked by a specific citizen.
    """
    citizen = db.query(User).filter(User.id == citizen_id, User.role == UserRole.CITIZEN).first()
    if not citizen:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CITIZEN_NOT_FOUND", "message": f"Citizen #{citizen_id} not found."}
        )

    parcels = db.query(Parcel).filter(Parcel.sender_id == citizen_id).order_by(Parcel.created_at.desc()).all()
    results = [
        OperationsCitizenParcelItem(
            id=p.id,
            tracking_id=p.tracking_id,
            receiver_name=p.receiver_name,
            receiver_phone=p.receiver_phone,
            destination_city=p.destination_city,
            destination_state=p.destination_state,
            destination_pin=p.destination_pin,
            parcel_type=p.parcel_type.value if hasattr(p.parcel_type, "value") else str(p.parcel_type),
            priority=p.priority.value if hasattr(p.priority, "value") else str(p.priority),
            weight=float(p.weight),
            price=float(p.price or 0.0),
            status=p.status,
            created_at=p.created_at
        )
        for p in parcels
    ]
    return ApiResponse.ok(data=results)


