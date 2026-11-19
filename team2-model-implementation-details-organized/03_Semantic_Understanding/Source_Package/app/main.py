
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.services.semantic_engine import analyze_semantic_understanding
from app.models.review_request import ReviewRequest

from app.services.review_service import (
    validate_review_request,
    get_saved_review_decision
)

from app.services.team1_handoff_service import generate_handoff


# --------------------------------------------------
# FastAPI Application
# --------------------------------------------------

app = FastAPI(
    title="Semantic Understanding API",
    description="Dataset semantic analysis, review and Team 1 handoff API",
    version="1.1.0"
)


# --------------------------------------------------
# CORS Configuration
# --------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# Home API
# --------------------------------------------------

@app.get("/")
def home():
    return {
        "message": "Semantic Understanding API is running",
        "version": "1.1.0"
    }


# --------------------------------------------------
# Health Check API
# --------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "semantic-understanding"
    }


# --------------------------------------------------
# Semantic Analysis API
# --------------------------------------------------

@app.get("/api/v1/semantic/analyze")
def analyze_dataset():
    try:
        return analyze_semantic_understanding()

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


# --------------------------------------------------
# Submit and Save Review Decisions
# --------------------------------------------------

@app.post("/api/v1/semantic/review")
def submit_review(request: ReviewRequest):
    try:
        result = validate_review_request(request)

        return {
            "status": "success",
            "message": "Review decisions validated and saved successfully",
            "data": result
        }

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )


# --------------------------------------------------
# Retrieve Saved Review Decisions
# --------------------------------------------------

@app.get("/api/v1/semantic/review/{dataset_id}")
def get_review(dataset_id: str):
    try:
        result = get_saved_review_decision(dataset_id)

        return {
            "status": "success",
            "message": "Review decisions retrieved successfully",
            "data": result
        }

    except FileNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error)
        )

    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error)
        )


# --------------------------------------------------
# Team 1 - Semantic Handoff API
# --------------------------------------------------

@app.get("/api/v1/semantic/handoff/{dataset_id}")
def get_semantic_handoff(dataset_id: str):
    try:
        result = generate_handoff(dataset_id)

        return {
            "status": "success",
            "message": "Semantic handoff generated successfully",
            "data": result
        }

    except FileNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error)
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )

