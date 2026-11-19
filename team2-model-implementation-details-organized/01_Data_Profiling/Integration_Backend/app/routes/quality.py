
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.quality_adapter import (
    SUPPORTED_RULES,
    check_data_quality,
    check_team1_data_quality
)

router = APIRouter(
    prefix="/api/v1/quality",
    tags=["Data Quality"]
)

BASE_DIR = Path(__file__).resolve().parents[2]
REGISTRY_FILE = BASE_DIR / "app" / "data" / "dataset_registry.json"


class QualityRequest(BaseModel):
    dataset_id: str
    version: str


class Team1QualityRequest(BaseModel):
    dataset_name: str
    file_path: str
    rules_to_apply: list[str] = Field(
        default_factory=lambda: SUPPORTED_RULES.copy()
    )
    target_col: str | None = None
    id_cols: list[str] = Field(default_factory=list)
    numeric_columns: list[str] = Field(default_factory=list)


def get_dataset(dataset_id):

    if not REGISTRY_FILE.exists():
        raise HTTPException(
            status_code=404,
            detail="Dataset registry not found"
        )

    try:
        with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
            datasets = json.load(f)

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


# Existing Team 2 endpoint
@router.post("/")
def validate_dataset(request: QualityRequest):

    dataset = get_dataset(request.dataset_id)

    file_path = (BASE_DIR / dataset["storage_path"]).resolve()

    if not file_path.is_relative_to(BASE_DIR):
        raise HTTPException(
            status_code=400,
            detail="Invalid dataset path"
        )

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Dataset file not found"
        )

    try:
        return check_data_quality(
            dataset_source=str(file_path),
            dataset_name=dataset["dataset_name"]
        )

    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail=str(e)
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Data quality validation failed."
        )


# Team 1 Data Quality endpoint
@router.post("/validate")
def validate_team1_dataset(request: Team1QualityRequest):

    file_path = Path(request.file_path)

    if not file_path.is_absolute():
        file_path = BASE_DIR / file_path

    file_path = file_path.resolve()

    if not file_path.is_relative_to(BASE_DIR):
        raise HTTPException(
            status_code=400,
            detail="Invalid dataset path"
        )

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Dataset file not found"
        )

    if file_path.suffix.lower() not in [".csv", ".xlsx", ".xls"]:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format"
        )

    try:
        return check_team1_data_quality(
            dataset_source=str(file_path),
            dataset_name=request.dataset_name,
            rules_to_apply=request.rules_to_apply,
            target_col=request.target_col,
            id_cols=request.id_cols,
            numeric_columns=request.numeric_columns
        )

    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail=str(e)
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Data quality validation failed."
        )
