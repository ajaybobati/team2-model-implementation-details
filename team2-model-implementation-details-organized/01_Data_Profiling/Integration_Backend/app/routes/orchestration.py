import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ConfigDict

from app.services.orchestration_service import run_dataset_services

router = APIRouter(
    prefix="/api/v1/orchestration",
    tags=["Orchestration"]
)

BASE_DIR = Path(__file__).resolve().parents[2]
REGISTRY_FILE = BASE_DIR / "app" / "data" / "dataset_registry.json"


class OrchestrationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_id: str = Field(min_length=1)
    request_id: Optional[str] = None
    dataset_name: Optional[str] = None
    target_col: Optional[str] = None
    id_cols: list[str] = Field(default_factory=list)
    options: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)


def get_dataset(dataset_id: str):

    if not REGISTRY_FILE.exists():
        raise HTTPException(
            status_code=404,
            detail="Dataset registry not found"
        )

    try:
        with open(REGISTRY_FILE, "r", encoding="utf-8") as file:
            datasets = json.load(file)

    except (json.JSONDecodeError, OSError):
        raise HTTPException(
            status_code=500,
            detail="Unable to read dataset registry"
        )

    for dataset in datasets:
        if dataset.get("dataset_id") == dataset_id:
            return dataset

    raise HTTPException(
        status_code=404,
        detail="Dataset not found"
    )


@router.post("/")
def orchestrate_dataset(request: OrchestrationRequest):

    dataset = get_dataset(request.dataset_id)

    dataset_source = BASE_DIR / dataset["storage_path"]

    if not dataset_source.exists():
        raise HTTPException(
            status_code=404,
            detail="Dataset file not found"
        )

    return run_dataset_services(
        dataset_source=str(dataset_source),
        dataset_id=request.dataset_id,
        request_id=request.request_id,
        dataset_name=request.dataset_name or dataset["dataset_name"],
        options=request.options,
        metadata=request.metadata,
        target_col=request.target_col,
        id_cols=request.id_cols or None
    )