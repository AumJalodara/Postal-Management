"""
Postal Document Retrieval API Endpoint.

Provides explainable, ranked retrieval over official postal legal chunks.
Supports:
- 'hybrid': Reciprocal Rank Fusion of PostgreSQL Lexical FTS and Local Dense Semantic Vectors (default)
- 'lexical': PostgreSQL tsvector + ts_rank_cd cover-density ranking
- 'dense': Local sentence-transformers/all-MiniLM-L6-v2 cosine similarity

Also provides grounded RAG via POST /ask.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.config import settings
from app.auth.limiter import limiter
from app.schemas.common import ApiResponse
from app.schemas.rag import RAGRequest, RAGResponse, RAG_VALID_MODES
from app.services.postal_retrieval_service import (
    PostalRetrievalService,
    RetrievalResponse,
    DEFAULT_TOP_K,
    MIN_TOP_K,
    MAX_TOP_K,
    MAX_QUERY_LENGTH
)
from app.services.rag_synthesis_service import RAGSynthesisService
from app.services.llm_provider import LLMProviderError

router = APIRouter(prefix="/postal", tags=["Postal Retrieval"])


class RetrievalRequest(BaseModel):
    query: str = Field(..., max_length=MAX_QUERY_LENGTH, description="Natural language or keyword search query.")
    top_k: int = Field(default=DEFAULT_TOP_K, ge=MIN_TOP_K, le=MAX_TOP_K, description="Number of results to retrieve (1-20).")
    document_type: Optional[str] = Field(default=None, description="Filter by document type (e.g. 'Act', 'Rules', 'Regulations', 'Amendment Regulations').")
    section_type: Optional[str] = Field(default=None, description="Filter by section type (e.g. 'section', 'rule', 'regulation', 'schedule', 'amendment').")
    document_id: Optional[str] = Field(default=None, description="Filter by document ID (e.g. 'DOC1', 'DOC2').")
    retrieval_mode: Optional[str] = Field(default=None, description="Retrieval mode: 'hybrid' (default), 'lexical', or 'dense'.")


@router.post("/retrieve", response_model=ApiResponse[RetrievalResponse])
@limiter.limit(settings.RATE_LIMIT_GENERAL)
def retrieve_postal_documents(
    request: Request,
    body: RetrievalRequest,
    db: Session = Depends(get_db)
):
    """
    Execute retrieval over the 228 verified postal legal chunks.
    Defaults to 'hybrid' (RRF of lexical and dense), with explicit support for 'lexical' and 'dense'.
    """
    service = PostalRetrievalService(db)
    response_data = service.search(
        query=body.query,
        top_k=body.top_k,
        document_type=body.document_type,
        section_type=body.section_type,
        document_id=body.document_id,
        mode=body.retrieval_mode
    )
    return ApiResponse.ok(data=response_data)


@router.get("/retrieve", response_model=ApiResponse[RetrievalResponse])
@limiter.limit(settings.RATE_LIMIT_GENERAL)
def retrieve_postal_documents_get(
    request: Request,
    query: str = Query(..., max_length=MAX_QUERY_LENGTH, description="Search query"),
    top_k: int = Query(default=DEFAULT_TOP_K, ge=MIN_TOP_K, le=MAX_TOP_K, description="Number of results"),
    document_type: Optional[str] = Query(default=None, description="Filter by document type"),
    section_type: Optional[str] = Query(default=None, description="Filter by section type"),
    document_id: Optional[str] = Query(default=None, description="Filter by document ID"),
    retrieval_mode: Optional[str] = Query(default=None, description="Retrieval mode: 'hybrid', 'lexical', or 'dense'"),
    db: Session = Depends(get_db)
):
    """
    GET endpoint for convenient browser, curl, and testing access.
    """
    service = PostalRetrievalService(db)
    response_data = service.search(
        query=query,
        top_k=top_k,
        document_type=document_type,
        section_type=section_type,
        document_id=document_id,
        mode=retrieval_mode
    )
    return ApiResponse.ok(data=response_data)


@router.post("/ask", response_model=ApiResponse[RAGResponse])
@limiter.limit(settings.RATE_LIMIT_RAG)
def ask_postal_question(
    request: Request,
    rag_request: RAGRequest,
    db: Session = Depends(get_db)
):
    """
    Grounded RAG endpoint: Ask a question about official postal regulations.

    The system retrieves relevant official postal documents, then generates
    a grounded explanation with citations mapping to actual source documents.

    This is an academic research prototype — not an official India Post service.
    """
    # Validate retrieval mode
    if rag_request.retrieval_mode not in RAG_VALID_MODES:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_RETRIEVAL_MODE",
                "message": f"Invalid retrieval_mode '{rag_request.retrieval_mode}'. "
                           f"Must be one of: {', '.join(sorted(RAG_VALID_MODES))}"
            }
        )

    try:
        rag_service = RAGSynthesisService(db=db)
        response = rag_service.ask(
            query=rag_request.query,
            top_k=rag_request.top_k,
            retrieval_mode=rag_request.retrieval_mode,
        )
        return ApiResponse.ok(data=response)
    except LLMProviderError as e:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "LLM_PROVIDER_ERROR",
                "message": f"LLM provider error: {str(e)}"
            }
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_REQUEST",
                "message": str(e)
            }
        )


@router.get("/states", response_model=ApiResponse[List[str]])
def get_postal_states():
    """
    Returns all 36 Indian States and Union Territories from the official postal directory.
    """
    from app.services.postal_location_service import postal_location_service
    states = postal_location_service.get_states()
    return ApiResponse.ok(data=states)


@router.get("/cities", response_model=ApiResponse[dict])
def get_postal_cities(state: str = Query(..., min_length=2, description="State / Union Territory name")):
    """
    Returns valid cities/districts and representative default PIN for the given state.
    """
    from app.services.postal_location_service import postal_location_service
    cities = postal_location_service.get_districts_for_state(state)
    default_pin = postal_location_service.get_default_pin_for_state(state)
    return ApiResponse.ok(data={
        "state": state,
        "cities": cities,
        "default_pin": default_pin,
        "count": len(cities)
    })


@router.get("/pincodes", response_model=ApiResponse[List[str]])
def get_postal_pincodes(
    state: Optional[str] = Query(None, description="Filter by state"),
    city: Optional[str] = Query(None, description="Filter by city/district"),
    limit: int = Query(default=100, ge=1, le=500, description="Max PINs to return")
):
    """
    Returns valid PIN codes for the selected state and/or city.
    """
    from app.services.postal_location_service import postal_location_service
    pins = postal_location_service.get_pincodes_for_location(state=state, district=city, limit=limit)
    return ApiResponse.ok(data=pins)


class AddressValidationRequest(BaseModel):
    state: str = Field(..., min_length=2, description="Selected State / UT")
    city: Optional[str] = Field(None, description="City / District name")
    pin: str = Field(..., min_length=6, max_length=6, description="6-digit PIN code")


@router.post("/validate-address", response_model=ApiResponse[dict])
def validate_address_endpoint(body: AddressValidationRequest):
    """
    Verifies geographic compatibility of state, city, and PIN to guarantee zero-mismatch bookings.
    """
    from app.services.postal_location_service import postal_location_service
    result = postal_location_service.validate_location(
        state=body.state,
        city=body.city,
        pin=body.pin
    )
    return ApiResponse.ok(data=result)


@router.get("/pincode/{pincode}")
def lookup_pincode(pincode: str):
    """
    Look up geographic and administrative details (city, district, state) for any 6-digit Indian PIN.
    """
    from app.services.postal_location_service import postal_location_service

    cleaned = pincode.strip()
    if len(cleaned) != 6 or not cleaned.isdigit() or cleaned.startswith("0"):
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_PIN", "message": "PIN code must contain exactly 6 digits and cannot start with 0."}
        )

    loc = postal_location_service.get_location_for_pin(cleaned)
    if not loc:
        raise HTTPException(
            status_code=404,
            detail={"code": "PIN_NOT_FOUND", "message": f"PIN code {cleaned} not found in official directory."}
        )

    city_name = loc.get("district") or loc.get("officename") or "City"
    state_name = loc.get("state") or ""

    return ApiResponse.ok(data={
        "pin": loc.get("pin"),
        "city": city_name.title(),
        "district": loc.get("district", "").title(),
        "state": state_name,
        "officename": loc.get("officename", "").title(),
        "latitude": loc.get("latitude"),
        "longitude": loc.get("longitude")
    })



@router.get("/available-pickup-hubs")
def get_available_pickup_hubs(db: Session = Depends(get_db)):
    """
    Return active postal pickup hubs, indicating agent coverage and state details.
    """
    from app.services.postal_location_service import postal_location_service
    from app.models.delivery_agent import DeliveryAgent

    # Fetch active agents
    agents = db.query(DeliveryAgent).filter(DeliveryAgent.is_available.is_(True)).all()
    active_pins = {a.service_area: a for a in agents}

    # Major priority state hubs
    priority_pins = [
        "110001", "400001", "600001", "560001", "700001", "500001",
        "380001", "302001", "226001", "682001", "160017", "800001", "751001"
    ]

    hubs = []
    seen = set()

    # 1. Active agent PINs first (instant dispatch available)
    for pin, agent in active_pins.items():
        loc = postal_location_service.get_location_for_pin(pin) or {}
        city = (loc.get("district") or loc.get("officename") or "Hub").title()
        state = loc.get("state", "").title()
        hubs.append({
            "pin": pin,
            "city": city,
            "state": state,
            "officename": loc.get("officename", f"Hub {pin}"),
            "has_active_agent": True,
            "agent_id": agent.id,
            "badge": "Active Agent Available (Instant Dispatch)"
        })
        seen.add(pin)

    # 2. Add other major state hubs
    for pin in priority_pins:
        if pin not in seen:
            loc = postal_location_service.get_location_for_pin(pin) or {}
            city = (loc.get("district") or loc.get("officename") or "Hub").title()
            state = loc.get("state", "").title()
            hubs.append({
                "pin": pin,
                "city": city,
                "state": state,
                "officename": loc.get("officename", f"Hub {pin}"),
                "has_active_agent": False,
                "agent_id": None,
                "badge": "State Hub (Queued for Assignment)"
            })
            seen.add(pin)

    return ApiResponse.ok(data=hubs)


