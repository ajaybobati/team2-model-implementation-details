
import json
from pathlib import Path
from typing import Any


# Project backend directory
BASE_DIR = Path(__file__).resolve().parents[2]

# JSON data directory
DATA_DIR = BASE_DIR / "data"


def load_json(file_name: str) -> Any:
    """
    Load a JSON file from the backend/data directory.
    Supports both JSON objects and JSON lists.
    """

    file_path = DATA_DIR / file_name

    if not file_path.exists():
        raise FileNotFoundError(
            f"JSON file not found: {file_path}"
        )

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)

    except json.JSONDecodeError as error:
        raise ValueError(
            f"Invalid JSON in {file_name}: {error}"
        ) from error


def load_profiling_data() -> dict:
    """
    Load dataset profiling information.
    Returns a dictionary containing dataset and column details.
    """

    return load_json(
        "input_profiling_Employee.profile.json"
    )


def load_quality_data() -> list:
    """
    Load dataset quality information.
    Returns a list containing quality details for multiple datasets.
    """

    return load_json(
        "input_quality_all_tables.json"
    )


def get_quality_data_by_dataset(dataset_name: str) -> dict | None:
    """
    Find quality information for a specific dataset.
    """

    quality_data = load_quality_data()

    for dataset in quality_data:
        if dataset.get("dataset", "").replace(".xlsx", "") == dataset_name:
            return dataset

    return None


def get_profiling_summary() -> dict:
    """
    Return a simplified profiling summary.
    """

    profiling = load_profiling_data()

    return {
        "dataset_id": profiling["dataset_reference"]["dataset_id"],
        "row_count": profiling["dataset"]["row_count"],
        "column_count": profiling["dataset"]["column_count"],
        "status": profiling["status"],
        "columns": profiling["columns"]
    }

