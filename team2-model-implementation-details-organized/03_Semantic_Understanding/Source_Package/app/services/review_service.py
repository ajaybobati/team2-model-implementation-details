
import json
from pathlib import Path

from app.models.review_request import ReviewRequest
from app.utils.json_loader import load_profiling_data


# Project directories
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
REVIEW_FILE = DATA_DIR / "saved_review_decisions.json"


# Validate and save review decisions
def validate_review_request(request: ReviewRequest) -> dict:

    profiling = load_profiling_data()

    dataset_id = profiling["dataset_reference"]["dataset_id"]

    if request.dataset_id != dataset_id:
        raise ValueError(f"Dataset mismatch. Expected: {dataset_id}")

    columns = profiling.get("columns", [])

    available_columns = {
        column["name"]: column for column in columns
    }

    # Validate target column
    if request.target is not None:

        if request.target not in available_columns:
            raise ValueError(
                f"Target column '{request.target}' does not exist."
            )

        if available_columns[request.target].get(
            "likely_identifier", False
        ):
            raise ValueError(
                f"'{request.target}' is an identifier and cannot be selected as target."
            )

    # Validate approved feature columns
    approved_features = request.approved_feature_columns

    if approved_features is not None:

        for feature in approved_features:

            if feature not in available_columns:
                raise ValueError(
                    f"Feature column '{feature}' does not exist."
                )

            if available_columns[feature].get(
                "likely_identifier", False
            ):
                raise ValueError(
                    f"'{feature}' is an identifier and cannot be approved as a feature."
                )

            if feature == request.target:
                raise ValueError(
                    "Target column cannot also be an approved feature."
                )

    # Review status
    target_confirmed = request.target is not None

    problem_type_confirmed = (
        request.problem_type is not None
        and request.problem_type != "review_required"
    )

    features_confirmed = (
        request.approved_feature_columns is not None
    )

    result = {
        "dataset_id": request.dataset_id,
        "goal": request.goal,
        "target": request.target,
        "problem_type": request.problem_type,
        "approved_feature_columns": approved_features,
        "target_status": (
            "approved" if target_confirmed else "pending"
        ),
        "problem_type_status": (
            "confirmed" if problem_type_confirmed else "pending"
        ),
        "features_status": (
            "approved" if features_confirmed else "pending"
        ),
        "review_complete": (
            target_confirmed
            and problem_type_confirmed
            and features_confirmed
        ),
        "training_allowed": False
    }

    # Save review decisions
    save_review_decision(result)

    return result


# Save review decisions into JSON
def save_review_decision(result: dict) -> None:

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if REVIEW_FILE.exists():

        with open(REVIEW_FILE, "r", encoding="utf-8") as file:
            saved_decisions = json.load(file)

    else:
        saved_decisions = {}

    saved_decisions[result["dataset_id"]] = result

    with open(REVIEW_FILE, "w", encoding="utf-8") as file:
        json.dump(saved_decisions, file, indent=4)


# Retrieve saved review decisions
def get_saved_review_decision(dataset_id: str) -> dict:

    if not REVIEW_FILE.exists():
        raise FileNotFoundError(
            "No saved review decisions found."
        )

    with open(REVIEW_FILE, "r", encoding="utf-8") as file:
        saved_decisions = json.load(file)

    if dataset_id not in saved_decisions:
        raise ValueError(
            f"No review decision found for dataset: {dataset_id}"
        )

    return saved_decisions[dataset_id]

