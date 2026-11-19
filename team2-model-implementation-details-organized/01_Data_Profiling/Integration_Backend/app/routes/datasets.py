import json
import uuid
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from threading import Lock

import pandas as pd
from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException,
    BackgroundTasks,
    Header
)
from fastapi.responses import JSONResponse

from app.services.orchestration_service import run_dataset_services

router = APIRouter(tags=["Datasets"])

BASE_DIR = Path(__file__).resolve().parents[2]
UPLOAD_DIR = BASE_DIR / "app" / "data" / "uploads"
RESULTS_DIR = BASE_DIR / "app" / "data" / "results"
REGISTRY_FILE = BASE_DIR / "app" / "data" / "dataset_registry.json"

REGISTRY_LOCK = Lock()

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def now():
    return datetime.now(timezone.utc).isoformat()


def load_registry():
    if not REGISTRY_FILE.exists():
        return []

    try:
        with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        raise HTTPException(
            status_code=500,
            detail="Dataset registry could not be read."
        )


def save_registry(datasets):
    temp_file = REGISTRY_FILE.with_suffix(".tmp")

    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(datasets, f, indent=4)

    temp_file.replace(REGISTRY_FILE)


def find_dataset(dataset_id):
    for dataset in load_registry():
        if dataset["dataset_id"] == dataset_id:
            return dataset

    raise HTTPException(
        status_code=404,
        detail="Dataset not found."
    )


def update_dataset(dataset_id, updates):
    with REGISTRY_LOCK:
        datasets = load_registry()

        for dataset in datasets:
            if dataset["dataset_id"] == dataset_id:
                dataset.update(updates)
                save_registry(datasets)
                return dataset

    raise HTTPException(
        status_code=404,
        detail="Dataset not found."
    )


def json_safe(value):
    return json.loads(
        json.dumps(value, default=str, allow_nan=False)
    )


def process_dataset_in_background(dataset_id):
    try:
        dataset = find_dataset(dataset_id)

        update_dataset(dataset_id, {
            "status": "validating",
            "processing_error": None
        })

        dataset_source = BASE_DIR / dataset["storage_path"]

        if not dataset_source.exists():
            raise FileNotFoundError("Uploaded dataset file not found.")

        # Validate the uploaded dataset.
        if dataset["file_format"] == "csv":
            df = pd.read_csv(dataset_source)
        else:
            df = pd.read_excel(dataset_source)

        if df.empty or len(df.columns) == 0:
            raise ValueError("Dataset contains no readable data.")

        update_dataset(dataset_id, {
            "status": "profiling",
            "rows": int(df.shape[0]),
            "columns": int(df.shape[1]),
            "column_names": list(df.columns.astype(str))
        })

        # Run Profiling and Quality services.
        result = run_dataset_services(
            dataset_source=str(dataset_source),
            dataset_id=dataset_id,
            dataset_name=dataset["dataset_name"]
        )

        safe_result = json_safe(result)

        result_path = RESULTS_DIR / f"{dataset_id}_results.json"

        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(safe_result, f, indent=4, allow_nan=False)

        final_status = (
            "ready"
            if result.get("status") in ["success", "warning"]
            else "failed"
        )

        update_dataset(dataset_id, {
            "status": final_status,
            "result_path": str(result_path.relative_to(BASE_DIR)),
            "processing_error": (
                None if final_status == "ready"
                else "One or more dataset services failed."
            ),
            "profiled_at": now()
        })

    except Exception as exc:
        update_dataset(dataset_id, {
            "status": "failed",
            "processing_error": str(exc)[:500]
        })


def run_dataset_profiling(dataset_id):
    dataset = find_dataset(dataset_id)

    if dataset.get("status") != "ready":
        raise HTTPException(
            status_code=409,
            detail="Dataset processing is not completed yet."
        )

    result_path = dataset.get("result_path")

    if not result_path:
        raise HTTPException(
            status_code=404,
            detail="Profiling result is not available."
        )

    file_path = BASE_DIR / result_path

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Saved profiling result was not found."
        )

    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/datasets")
def list_datasets():
    datasets = load_registry()

    return {
        "status": "success",
        "total": len(datasets),
        "datasets": datasets
    }


@router.get("/datasets/{dataset_id}")
def get_dataset(dataset_id: str):
    return {
        "status": "success",
        "dataset": find_dataset(dataset_id)
    }
@router.post("/api/v1/datasets/{dataset_id}/retry")
def retry_dataset(
    dataset_id: str,
    background_tasks: BackgroundTasks
):
    dataset = find_dataset(dataset_id)

    if dataset.get("status") in ["validating", "profiling"]:
        raise HTTPException(
            status_code=409,
            detail="Dataset processing is already in progress."
        )

    if dataset.get("status") != "failed":
        raise HTTPException(
            status_code=409,
            detail="Only failed datasets can be retried."
        )

    storage_path = dataset.get("storage_path")

    if not storage_path:
        raise HTTPException(
            status_code=404,
            detail="Dataset file reference is missing."
        )

    dataset_source = BASE_DIR / storage_path

    if not dataset_source.exists():
        raise HTTPException(
            status_code=404,
            detail="Dataset file not found."
        )

    update_dataset(dataset_id, {
        "status": "uploaded",
        "result_path": None,
        "processing_error": None,
        "profiled_at": None
    })

    background_tasks.add_task(
        process_dataset_in_background,
        dataset_id
    )

    return JSONResponse(
        status_code=202,
        content={
            "status": "accepted",
            "message": "Dataset retry processing started.",
            "dataset_id": dataset_id
        }
    )

@router.get("/api/v1/datasets/{dataset_id}/profile")
def get_dataset_profile(dataset_id: str):
    return run_dataset_profiling(dataset_id)


@router.post("/api/v1/datasets/{dataset_id}/profile")
def create_dataset_profile(
    dataset_id: str,
    background_tasks: BackgroundTasks
):
    dataset = find_dataset(dataset_id)

    if not dataset.get("storage_path"):
        raise HTTPException(
            status_code=404,
            detail="Dataset file reference is missing."
        )

    dataset_source = BASE_DIR / dataset["storage_path"]

    if not dataset_source.exists():
        raise HTTPException(
            status_code=404,
            detail="Dataset file not found."
        )

    if dataset.get("status") in ["validating", "profiling"]:
        raise HTTPException(
            status_code=409,
            detail="Dataset processing is already in progress."
        )

    update_dataset(dataset_id, {
        "status": "uploaded",
        "processing_error": None,
        "result_path": None
    })

    background_tasks.add_task(
        process_dataset_in_background,
        dataset_id
    )

    return JSONResponse(
        status_code=202,
        content={
            "status": "accepted",
            "message": "Dataset profiling and quality processing started.",
            "dataset_id": dataset_id
        }
    )
@router.post("/api/v1/datasets/upload")
async def upload_dataset(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key"
    )
):
    original_name = Path(file.filename or "").name
    extension = Path(original_name).suffix.lower()

    if extension not in [".csv", ".xlsx"]:
        raise HTTPException(
            status_code=400,
            detail="Only CSV and XLSX files are supported."
        )

    dataset_id = str(uuid.uuid4())
    stored_name = f"{dataset_id}{extension}"
    file_path = UPLOAD_DIR / stored_name

    try:
        content = await file.read()

        if not content:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty."
            )

        file_hash = hashlib.sha256(content).hexdigest()

        with open(file_path, "wb") as f:
            f.write(content)

        if extension == ".csv":
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)

        if df.empty or len(df.columns) == 0:
            raise HTTPException(
                status_code=400,
                detail="Dataset contains no readable data."
            )

        dataset = {
            "dataset_id": dataset_id,
            "dataset_name": original_name,
            "file_name": stored_name,
            "file_format": extension.lstrip("."),
            "rows": int(df.shape[0]),
            "columns": int(df.shape[1]),
            "column_names": list(df.columns.astype(str)),
            "uploaded_at": now(),
            "storage_path": str(file_path.relative_to(BASE_DIR)),
            "status": "uploaded",
            "result_path": None,
            "processing_error": None,
            "idempotency_key": idempotency_key,
            "file_hash": file_hash
        }

        with REGISTRY_LOCK:
            datasets = load_registry()

            if idempotency_key:
                existing = next(
                    (
                        item for item in datasets
                        if item.get("idempotency_key") == idempotency_key
                    ),
                    None
                )

                if existing:
                    file_path.unlink(missing_ok=True)

                    if existing.get("file_hash") != file_hash:
                        raise HTTPException(
                            status_code=409,
                            detail="Idempotency key already used with a different file."
                        )

                    return JSONResponse(
                        status_code=200 if existing.get("status") == "ready" else 202,
                        content={
                            "status": "duplicate_request",
                            "message": "This upload was already received.",
                            "dataset": existing
                        }
                    )

            datasets.append(dataset)
            save_registry(datasets)

        background_tasks.add_task(
            process_dataset_in_background,
            dataset_id
        )

        return JSONResponse(
            status_code=202,
            content={
                "status": "accepted",
                "message": "Dataset uploaded. Background processing started.",
                "dataset": dataset
            }
        )

    except HTTPException:
        file_path.unlink(missing_ok=True)
        raise

    except Exception:
        file_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=400,
            detail="Unable to upload the dataset."
        )

    finally:
        await file.close()

